"""Step 19 automatic execution pipeline.

This module wires approved project stages into a deterministic local
orchestration summary. It validates stage contracts and boundaries, but it does
not redefine or execute score formulas, ranking semantics, report semantics,
backtest semantics, or valuation/fundamental scoring.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tomllib
from typing import Any

from src.pipeline.contracts import (
    PipelineRunMode,
    PipelineRunSummary,
    PipelineStageContract,
    PipelineStageResult,
    PipelineStageStatus,
)
from src.validation.step19_pipeline_guardrails import (
    STEP19_CANONICAL_STAGE_ORDER,
    STEP19_PIPELINE_NOTICE,
    validate_step19_generated_output_path,
    validate_step19_pipeline_config,
    validate_step19_pipeline_summary,
)


DEFAULT_STEP19_PIPELINE_CONFIG = Path("config/step19_pipeline.toml")

STEP19_STAGE_ALIASES: Mapping[str, str] = {
    "ranking": "latest_ranking",
    "latest_ranking": "latest_ranking",
    "detail_report": "security_detail_reports",
    "detail_reports": "security_detail_reports",
    "security_detail_report": "security_detail_reports",
    "security_detail_reports": "security_detail_reports",
    "backtest": "conservative_backtest_optional",
    "conservative_backtest": "conservative_backtest_optional",
    "valuation_candidate_validation": "candidate_valuation_boundary_check_optional",
    "candidate_valuation_boundary": "candidate_valuation_boundary_check_optional",
    "validation_only": "output_validation",
}

STEP19_ALWAYS_INCLUDED_STAGES = (
    "preflight",
    "context_check",
    "output_validation",
    "final_summary",
)

NO_SEMANTICS_CHANGED_NOTICE = (
    "No scoring formula, technical_composite_score semantics, "
    "final_composite_score semantics, Step 15 ranking semantics, Step 16 report "
    "semantics, Step 17 backtest semantics, or Step 18 candidate-only boundary "
    "was changed by this Step 19 pipeline."
)


def load_pipeline_config(path: str | Path = DEFAULT_STEP19_PIPELINE_CONFIG) -> dict[str, Any]:
    """Load a Step 19 TOML config."""

    config_path = Path(path)
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def build_default_stage_contracts(
    config: Mapping[str, Any] | None = None,
) -> tuple[PipelineStageContract, ...]:
    """Build deterministic stage contracts from config or defaults."""

    if config is None:
        config = {}
    stage_config = config.get("stages", {}) if isinstance(config, Mapping) else {}
    if not isinstance(stage_config, Mapping) or not stage_config:
        return _default_contracts()

    order_lookup = {stage: index * 10 for index, stage in enumerate(STEP19_CANONICAL_STAGE_ORDER, start=1)}
    contracts = [
        PipelineStageContract.from_mapping(
            str(stage_name),
            dict(values) if isinstance(values, Mapping) else {},
            order=order_lookup.get(str(stage_name), 10_000 + index),
        )
        for index, (stage_name, values) in enumerate(stage_config.items(), start=1)
    ]
    return tuple(sorted(contracts, key=lambda item: (item.order, item.stage_name)))


def run_step19_pipeline(
    *,
    config_path: str | Path = DEFAULT_STEP19_PIPELINE_CONFIG,
    run_mode: str | PipelineRunMode | None = None,
    selected_stages: Sequence[str] | None = None,
    summary_output_path: str | Path | None = None,
    write_summary: bool = False,
    generated_at: str | None = None,
    git_commit: str | None = None,
    project_root: str | Path | None = None,
) -> PipelineRunSummary:
    """Run the Step 19 orchestration layer and return a structured summary."""

    root = Path(project_root) if project_root is not None else Path.cwd()
    config = load_pipeline_config(config_path)
    validate_step19_pipeline_config(config)
    resolved_mode = _resolve_run_mode(run_mode, config)
    contracts = build_default_stage_contracts(config)
    selected_names = _resolve_selected_stage_names(selected_stages, contracts)

    stage_results = tuple(
        _run_stage_contract(
            contract,
            run_mode=resolved_mode,
            project_root=root,
            selected=contract.stage_name in selected_names,
        )
        for contract in contracts
    )
    skipped_stages = tuple(
        result.stage_name
        for result in stage_results
        if result.status == PipelineStageStatus.SKIPPED
    )
    forbidden_scope_check = _forbidden_scope_check(config, stage_results)
    summary = PipelineRunSummary(
        run_mode=resolved_mode,
        generated_at=generated_at or _utc_timestamp(),
        stages=stage_results,
        overall_status=_overall_status(stage_results),
        validation_summary=_validation_summary(stage_results, resolved_mode),
        forbidden_scope_check=forbidden_scope_check,
        no_semantics_changed_notice=NO_SEMANTICS_CHANGED_NOTICE,
        selected_stages=tuple(
            contract.stage_name
            for contract in contracts
            if contract.stage_name in selected_names
        ),
        skipped_stages=skipped_stages,
        git_commit=git_commit or _git_commit_or_unknown(root),
        boundary_notice=STEP19_PIPELINE_NOTICE,
    )
    validate_step19_pipeline_summary(summary)
    if write_summary or summary_output_path is not None:
        if summary_output_path is None:
            summary_output_path = "reports/pipeline/generated/step19_pipeline_summary.json"
        _write_summary(summary, Path(summary_output_path), project_root=root)
    return summary


def _run_stage_contract(
    contract: PipelineStageContract,
    *,
    run_mode: PipelineRunMode,
    project_root: Path,
    selected: bool,
) -> PipelineStageResult:
    warnings: list[str] = []
    errors: list[str] = []
    boundary_notes = list(contract.boundary_notes)
    validation_status = "passed"

    if not selected:
        return PipelineStageResult(
            stage_name=contract.stage_name,
            status=PipelineStageStatus.SKIPPED,
            input_refs=contract.input_refs,
            output_refs=(),
            warnings=("stage not selected",),
            boundary_notes=tuple(boundary_notes),
            validation_status="not_run",
        )
    if not contract.enabled:
        return PipelineStageResult(
            stage_name=contract.stage_name,
            status=PipelineStageStatus.SKIPPED,
            input_refs=contract.input_refs,
            output_refs=(),
            warnings=("stage disabled by config",),
            boundary_notes=tuple(boundary_notes),
            validation_status="not_run",
        )

    missing_inputs = _missing_required_inputs(contract, project_root)
    if missing_inputs:
        errors.append(
            "missing required input path(s): " + ", ".join(missing_inputs)
        )
        validation_status = "failed"
        return PipelineStageResult(
            stage_name=contract.stage_name,
            status=PipelineStageStatus.BLOCKED,
            input_refs=contract.input_refs,
            output_refs=contract.output_refs,
            warnings=tuple(warnings),
            errors=tuple(errors),
            boundary_notes=tuple(boundary_notes),
            validation_status=validation_status,
        )

    if run_mode == PipelineRunMode.DRY_RUN:
        warnings.append("dry-run only; no production output written")
        status = PipelineStageStatus.READY
    elif run_mode == PipelineRunMode.VALIDATE_ONLY:
        warnings.append("validate-only mode; stage execution not invoked")
        status = PipelineStageStatus.COMPLETED
    else:
        warnings.append(
            "contract-validation execution only; existing component semantics are unchanged"
        )
        status = PipelineStageStatus.COMPLETED

    return PipelineStageResult(
        stage_name=contract.stage_name,
        status=status,
        input_refs=contract.input_refs,
        output_refs=contract.output_refs if run_mode != PipelineRunMode.DRY_RUN else (),
        warnings=tuple(warnings),
        errors=tuple(errors),
        boundary_notes=tuple(boundary_notes),
        validation_status=validation_status,
    )


def _resolve_run_mode(
    run_mode: str | PipelineRunMode | None,
    config: Mapping[str, Any],
) -> PipelineRunMode:
    if isinstance(run_mode, PipelineRunMode):
        return run_mode
    value = run_mode
    if value is None:
        step19 = config.get("step19", {})
        value = step19.get("default_run_mode", PipelineRunMode.DRY_RUN.value) if isinstance(step19, Mapping) else PipelineRunMode.DRY_RUN.value
    try:
        return PipelineRunMode(str(value))
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in PipelineRunMode)
        raise ValueError(f"unsupported Step 19 run mode: {value}. Allowed: {allowed}") from exc


def _resolve_selected_stage_names(
    selected_stages: Sequence[str] | None,
    contracts: Sequence[PipelineStageContract],
) -> frozenset[str]:
    known = _contract_names(contracts)
    if not selected_stages:
        return frozenset(known)

    resolved: set[str] = set(STEP19_ALWAYS_INCLUDED_STAGES).intersection(known)
    for stage in selected_stages:
        normalized = _normalize_stage_name(stage)
        canonical = STEP19_STAGE_ALIASES.get(normalized, normalized)
        if canonical not in known:
            raise ValueError(f"unknown Step 19 stage selection: {stage}")
        resolved.add(canonical)
    return frozenset(resolved)


def _normalize_stage_name(stage: str) -> str:
    return str(stage).strip().lower().replace("-", "_").replace(" ", "_")


def _contract_names(contracts: Sequence[PipelineStageContract]) -> frozenset[str]:
    return frozenset(contract.stage_name for contract in contracts)


def _missing_required_inputs(
    contract: PipelineStageContract,
    project_root: Path,
) -> tuple[str, ...]:
    missing: list[str] = []
    for input_path in contract.required_input_paths:
        candidate = Path(input_path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        if not candidate.exists():
            missing.append(input_path)
    return tuple(missing)


def _overall_status(results: Sequence[PipelineStageResult]) -> PipelineStageStatus:
    if any(result.status == PipelineStageStatus.FAILED for result in results):
        return PipelineStageStatus.FAILED
    if any(result.status == PipelineStageStatus.BLOCKED for result in results):
        return PipelineStageStatus.BLOCKED
    return PipelineStageStatus.COMPLETED


def _validation_summary(
    results: Sequence[PipelineStageResult],
    run_mode: PipelineRunMode,
) -> dict[str, Any]:
    counts = {status.value: 0 for status in PipelineStageStatus}
    for result in results:
        counts[result.status.value] += 1
    return {
        "status": "passed"
        if counts[PipelineStageStatus.BLOCKED.value] == 0
        and counts[PipelineStageStatus.FAILED.value] == 0
        else "blocked",
        "run_mode": run_mode.value,
        "stage_counts": counts,
        "dry_run_default_safe": run_mode == PipelineRunMode.DRY_RUN,
        "network_required": False,
        "secrets_required": False,
        "market_cache_required": False,
    }


def _forbidden_scope_check(
    config: Mapping[str, Any],
    results: Sequence[PipelineStageResult],
) -> dict[str, Any]:
    config_result = validate_step19_pipeline_config(config, raise_on_error=False)
    blocked_stage_errors = [
        f"{result.stage_name}: {'; '.join(result.errors)}"
        for result in results
        if result.errors
    ]
    errors = [*config_result.errors, *blocked_stage_errors]
    return {
        "status": "passed" if not errors else "blocked",
        "errors": errors,
        "warnings": list(config_result.warnings),
        "checked_items": [
            "dry_run default",
            "no network or secrets",
            "no valuation/fundamental activation",
            "no return feedback loop",
            "no report feedback into scoring",
            "no Step 20 completion claim",
            "generated output path boundary",
        ],
    }


def _write_summary(
    summary: PipelineRunSummary,
    output_path: Path,
    *,
    project_root: Path,
) -> None:
    path_text = str(output_path).replace("\\", "/")
    validate_step19_generated_output_path(path_text)
    resolved = output_path if output_path.is_absolute() else project_root / output_path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git_commit_or_unknown(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    value = result.stdout.strip()
    return value or "unknown"


def _default_contracts() -> tuple[PipelineStageContract, ...]:
    contracts: list[PipelineStageContract] = []
    for index, stage_name in enumerate(STEP19_CANONICAL_STAGE_ORDER, start=1):
        contracts.append(
            PipelineStageContract(
                stage_name=stage_name,
                order=index * 10,
                optional=stage_name.endswith("_optional"),
                implementation_ref=_default_implementation_ref(stage_name),
                input_refs=_default_input_refs(stage_name),
                output_refs=_default_output_refs(stage_name),
                forbidden_inputs=_default_forbidden_inputs(stage_name),
                allowed_generated_outputs=_default_allowed_outputs(stage_name),
                validation_expectations=_default_validation_expectations(stage_name),
                boundary_notes=_default_boundary_notes(stage_name),
            )
        )
    return tuple(contracts)


def _default_implementation_ref(stage_name: str) -> str:
    refs = {
        "data_preprocess": "src.preprocess.daily_ohlcv",
        "technical_indicators": "src.indicators.technical",
        "raw_scores": "src.scores.technical_scores",
        "normalized_scores": "src.scores.normalization_timeseries / normalization_cross_sectional",
        "composite_or_adoption_context": "src.selection.adoption_synthesis",
        "latest_ranking": "src.scanner.latest_ranking",
        "security_detail_reports": "src.reports.security_detail_report",
        "conservative_backtest_optional": "Quant_mvp.backtest_mvp.engine",
        "candidate_valuation_boundary_check_optional": "src.valuation.validation",
        "output_validation": "src.validation.step15/16/17/18 guardrails",
    }
    return refs.get(stage_name, "Step 19 orchestration")


def _default_input_refs(stage_name: str) -> tuple[str, ...]:
    refs = {
        "latest_ranking": ("Step 10 normalized technical scores", "Step 14 adoption synthesis"),
        "security_detail_reports": ("Step 15 latest ranking output",),
        "conservative_backtest_optional": (
            "Step 15/16 frozen technical ranking context",
            "OHLCV price input",
        ),
        "candidate_valuation_boundary_check_optional": (
            "Step 18 candidate valuation/fundamental records",
        ),
    }
    return refs.get(stage_name, ())


def _default_output_refs(stage_name: str) -> tuple[str, ...]:
    refs = {
        "latest_ranking": ("Step 15 latest ranking snapshot",),
        "security_detail_reports": ("reports/security/generated/",),
        "conservative_backtest_optional": ("reports/backtest/generated/",),
        "candidate_valuation_boundary_check_optional": ("reports/valuation/generated/",),
        "final_summary": ("reports/pipeline/generated/step19_pipeline_summary.json",),
    }
    return refs.get(stage_name, ())


def _default_forbidden_inputs(stage_name: str) -> tuple[str, ...]:
    common = (
        "valuation_score",
        "fundamental_score",
        "future_return",
        "forward_return",
        "expected_return",
        "trading_signal",
        "external_network_data",
    )
    if stage_name == "conservative_backtest_optional":
        return (*common, "valuation/fundamental candidate data")
    return common


def _default_allowed_outputs(stage_name: str) -> tuple[str, ...]:
    if stage_name == "security_detail_reports":
        return ("reports/security/generated/",)
    if stage_name == "conservative_backtest_optional":
        return ("reports/backtest/generated/",)
    if stage_name == "candidate_valuation_boundary_check_optional":
        return ("reports/valuation/generated/",)
    if stage_name == "final_summary":
        return ("reports/pipeline/generated/",)
    return ()


def _default_validation_expectations(stage_name: str) -> tuple[str, ...]:
    if stage_name == "latest_ranking":
        return ("Step 15 guardrails pass", "no valuation/fundamental columns")
    if stage_name == "security_detail_reports":
        return ("Step 16 report guardrails pass", "rank fields remain read-only")
    if stage_name == "conservative_backtest_optional":
        return ("Step 17 guardrails pass", "no return feedback to upstream inputs")
    if stage_name == "candidate_valuation_boundary_check_optional":
        return ("Step 18 guardrails pass", "candidate-only inactive boundary")
    return ("Step 19 pipeline guardrails pass",)


def _default_boundary_notes(stage_name: str) -> tuple[str, ...]:
    notes = {
        "latest_ranking": (
            "Step 15 remains the ranking source; Step 19 does not re-rank securities.",
        ),
        "security_detail_reports": (
            "Step 16 reports read ranking context and do not create new ranking.",
        ),
        "conservative_backtest_optional": (
            "Step 17 remains evaluation-only; returns do not feed upstream.",
        ),
        "candidate_valuation_boundary_check_optional": (
            "Step 18 valuation/fundamental data remains candidate-only and inactive.",
        ),
    }
    return notes.get(stage_name, ("Step 19 orchestration boundary preserved.",))


__all__ = (
    "DEFAULT_STEP19_PIPELINE_CONFIG",
    "NO_SEMANTICS_CHANGED_NOTICE",
    "STEP19_STAGE_ALIASES",
    "build_default_stage_contracts",
    "load_pipeline_config",
    "run_step19_pipeline",
)
