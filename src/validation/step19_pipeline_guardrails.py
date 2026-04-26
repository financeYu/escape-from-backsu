"""Guardrails for the Step 19 automatic execution pipeline.

These checks validate orchestration contracts and summaries. They do not run
ranking, report, backtest, valuation, score, or data-ingestion logic.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
import re
from pathlib import PurePosixPath
from typing import Any

from src.validation.common import string_tuple
from src.validation.field_guardrails import (
    find_forbidden_field_refs as _find_common_forbidden_field_refs,
)
from src.validation.text_guardrails import find_forbidden_pattern_labels


STEP19_PIPELINE_NOTICE = (
    "Step 19 automatic execution pipeline summary only; no scoring, ranking, "
    "report, backtest, or valuation semantics changed."
)

STEP19_CANONICAL_STAGE_ORDER: tuple[str, ...] = (
    "preflight",
    "context_check",
    "data_preprocess",
    "technical_indicators",
    "raw_scores",
    "normalized_scores",
    "composite_or_adoption_context",
    "latest_ranking",
    "security_detail_reports",
    "conservative_backtest_optional",
    "candidate_valuation_boundary_check_optional",
    "output_validation",
    "final_summary",
)

STEP19_UPSTREAM_STAGES_BEFORE_REPORT = frozenset(
    {
        "data_preprocess",
        "technical_indicators",
        "raw_scores",
        "normalized_scores",
        "composite_or_adoption_context",
        "latest_ranking",
    }
)

STEP19_UPSTREAM_STAGES = frozenset(
    {
        "data_preprocess",
        "technical_indicators",
        "raw_scores",
        "normalized_scores",
        "composite_or_adoption_context",
        "latest_ranking",
        "security_detail_reports",
    }
)

STEP19_BACKTEST_STAGES = frozenset({"conservative_backtest_optional", "backtest"})
STEP19_REPORT_STAGES = frozenset({"security_detail_reports", "detail_report"})

STEP19_FORBIDDEN_OUTPUT_FIELDS = frozenset(
    {
        "valuation_score",
        "fundamental_score",
        "valuation_candidate_score",
        "fundamental_candidate_score",
        "future_return",
        "forward_return",
        "expected_return",
        "target_return",
        "next_return",
        "next_period_return",
        "realized_return",
        "realized_pnl",
        "alpha",
        "alpha_signal",
        "signal",
        "buy",
        "sell",
        "hold",
        "recommendation",
        "trading_signal",
        "target_price",
        "position_size",
    }
)

STEP19_RETURN_FEEDBACK_FIELDS = frozenset(
    {
        "future_return",
        "forward_return",
        "expected_return",
        "target_return",
        "next_return",
        "next_period_return",
        "realized_return",
        "realized_holding_return",
        "evaluation_return",
        "backtest_period_return",
        "portfolio_return",
        "strategy_return",
        "benchmark_return",
        "excess_return",
        "sharpe",
        "mdd",
        "drawdown",
        "cagr",
        "win_rate",
        "hit_rate",
        "hit_ratio",
    }
)

STEP19_FORBIDDEN_STAGE_TOKENS = (
    "valuation_score",
    "fundamental_score",
    "valuation_aware",
    "fundamental_scoring",
    "kosdaq150",
    "futures",
    "options",
    "external_data_ingestion",
    "network_ingestion",
    "step20",
)

STEP19_FORBIDDEN_LANGUAGE_PATTERNS: Mapping[str, str] = {
    "alpha proven": r"\balpha\s+(?:is\s+)?proven\b|\bproven\s+alpha\b",
    "predictive alpha": r"\bpredictive\s+alpha\b",
    "profitable": r"\bprofitable\b|\bprofitability\s+proven\b",
    "market beating": r"\bmarket[-\s]?beating\b|\boutperform(?:s|ed|ing)?\s+the\s+market\b",
    "buy recommendation": r"\bbuy\s+(?:signal|recommendation|call|setup)\b",
    "sell recommendation": r"\bsell\s+(?:signal|recommendation|call|setup)\b",
    "hold recommendation": r"\bhold\s+(?:signal|recommendation|call|setup)\b",
    "trading signal": r"\btrading\s+signal\b",
    "trading recommendation": r"\btrading\s+recommendation\b",
    "investment recommendation": r"\binvestment\s+recommendation\b",
    "expected return": r"\bexpected[_\s-]?return\b",
    "target price": r"\btarget[_\s-]?price\b|\bprice\s+target\b",
    "valuation score": r"\bvaluation[_\s-]?score\b",
    "fundamental score": r"\bfundamental[_\s-]?score\b",
}

STEP19_STEP20_COMPLETION_PATTERNS: Mapping[str, str] = {
    "step20 complete": r"\bstep\s*20\b.{0,32}\b(?:complete|completed|done|passed)\b",
    "final done validation complete": (
        r"\bfinal\s+done\s+validation\b.{0,32}\b(?:complete|completed|done|passed)\b"
    ),
}

STEP19_GENERATED_OUTPUT_PREFIXES = (
    "reports/pipeline/generated/",
    "reports/security/generated/",
    "reports/backtest/generated/",
    "reports/valuation/generated/",
)

STEP19_FORBIDDEN_OUTPUT_PATH_PREFIXES = (
    "data/",
    "cache/",
    "outputs/",
    "chart_mvp/data/",
    "chart_mvp/outputs/",
    "chart_mvp/cache/",
    "chart_mvp/reports/",
    "reports/data_quality/",
)


@dataclass(frozen=True)
class Step19PipelineGuardrailResult:
    """Validation result for Step 19 pipeline guardrails."""

    context: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    forbidden_language: tuple[str, ...] = ()
    forbidden_fields: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether validation passed."""

        return not self.errors

    @property
    def valid(self) -> bool:
        """Alias for callers that prefer shorter names."""

        return self.is_valid

    def raise_for_errors(self) -> None:
        """Raise ValueError when validation failed."""

        if self.errors:
            raise ValueError(f"{self.context} failed Step 19 validation: {'; '.join(self.errors)}")

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable result."""

        return {
            "context": self.context,
            "status": "passed" if self.is_valid else "failed",
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "forbidden_language": list(self.forbidden_language),
            "forbidden_fields": list(self.forbidden_fields),
        }


def validate_step19_pipeline_config(
    config: Mapping[str, Any],
    *,
    context: str = "Step 19 pipeline config",
    raise_on_error: bool = True,
) -> Step19PipelineGuardrailResult:
    """Validate Step 19 config without executing domain stages."""

    errors: list[str] = []
    warnings: list[str] = []

    step19 = _mapping(config.get("step19"))
    default_mode = str(step19.get("default_run_mode", "dry_run"))
    if default_mode != "dry_run":
        errors.append("default_run_mode must be dry_run")
    _assert_false_flag(step19, "network_allowed", errors)
    _assert_false_flag(step19, "secrets_allowed", errors)
    _assert_false_flag(step19, "local_cache_required", errors)

    boundary = _mapping(config.get("boundary"))
    for flag in (
        "valuation_fundamental_scoring_activation",
        "technical_composite_score_integration",
        "final_composite_score_activation",
        "kosdaq150_expansion",
        "futures_expansion",
        "options_expansion",
        "external_data_ingestion",
        "step20_final_validation",
    ):
        _assert_false_flag(boundary, flag, errors)
    if boundary.get("no_semantics_changed", True) is not True:
        errors.append("boundary.no_semantics_changed must be true")

    stages = _mapping(config.get("stages"))
    if not stages:
        errors.append("stages must define at least one Step 19 stage")
    _validate_stage_order(stages, errors)
    _validate_stage_contracts(stages, errors, warnings)
    _validate_feedback_edges(stages, errors)

    result = Step19PipelineGuardrailResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(warnings),
        forbidden_fields=tuple(_find_config_forbidden_fields(stages)),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def validate_step19_pipeline_summary(
    summary: Mapping[str, Any] | Any,
    *,
    context: str = "Step 19 pipeline summary",
    raise_on_error: bool = True,
) -> Step19PipelineGuardrailResult:
    """Validate a structured Step 19 run summary."""

    summary_dict = summary.to_dict() if hasattr(summary, "to_dict") else dict(summary)
    errors: list[str] = []
    warnings: list[str] = []
    text = _json_text(summary_dict)

    forbidden_language = find_step19_forbidden_language(text)
    if forbidden_language:
        errors.append(f"contains forbidden language: {', '.join(forbidden_language)}")

    step20_claims = find_step20_completion_claims(text)
    if step20_claims:
        errors.append(f"contains Step 20 completion claim: {', '.join(step20_claims)}")

    forbidden_fields = _validate_summary_stages(summary_dict, errors)

    if summary_dict.get("run_mode") != "dry_run":
        warnings.append("non-dry-run summary should remain summary-only unless stage inputs are explicit")

    result = Step19PipelineGuardrailResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(warnings),
        forbidden_language=tuple(forbidden_language),
        forbidden_fields=tuple(sorted(forbidden_fields)),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def _validate_summary_stages(summary_dict: Mapping[str, Any], errors: list[str]) -> set[str]:
    stages = summary_dict.get("stages", ())
    if not isinstance(stages, Iterable):
        errors.append("summary.stages must be iterable")
        return set()

    forbidden_fields: set[str] = set()
    for stage in stages:
        if not isinstance(stage, Mapping):
            errors.append("summary stage result must be a mapping")
            continue
        forbidden_fields.update(_validate_summary_stage(stage, errors))
    return forbidden_fields


def _validate_summary_stage(stage: Mapping[str, Any], errors: list[str]) -> set[str]:
    stage_name = str(stage.get("stage_name", ""))
    if not stage_name:
        errors.append("summary stage is missing stage_name")
    status = str(stage.get("status", ""))
    if not status:
        errors.append(f"{stage_name or 'unknown stage'} is missing status")

    forbidden_fields: set[str] = set()
    for key in ("input_refs", "output_refs"):
        for ref in string_tuple(stage.get(key, ())):
            forbidden_fields.update(_find_forbidden_field_refs((ref,)))
            if key == "output_refs":
                path_error = _generated_output_path_error(ref)
                if path_error:
                    errors.append(path_error)
    return forbidden_fields


def validate_step19_generated_output_path(path: str, *, context: str = "Step 19 output path") -> None:
    """Reject generated-output paths that would pollute source-controlled data/cache areas."""

    error = _generated_output_path_error(path)
    if error:
        raise ValueError(f"{context}: {error}")


def find_step19_forbidden_language(text: str) -> list[str]:
    """Return forbidden Step 19 language labels in text."""

    return find_forbidden_pattern_labels(
        text,
        STEP19_FORBIDDEN_LANGUAGE_PATTERNS,
        is_allowed_match=_is_allowed_negated_match,
    )


def find_step20_completion_claims(text: str) -> list[str]:
    """Return Step 20 completion claim labels in text."""

    return find_forbidden_pattern_labels(
        text,
        STEP19_STEP20_COMPLETION_PATTERNS,
        is_allowed_match=_is_allowed_negated_match,
    )


def _validate_stage_order(stages: Mapping[str, Any], errors: list[str]) -> None:
    orders: list[int] = []
    for stage_name, stage_values in stages.items():
        values = _mapping(stage_values)
        if _is_forbidden_stage_name(str(stage_name)):
            errors.append(f"forbidden stage name: {stage_name}")
        order = values.get("order")
        if order is None:
            errors.append(f"{stage_name} missing order")
            continue
        try:
            orders.append(int(order))
        except (TypeError, ValueError):
            errors.append(f"{stage_name} order must be an integer")
    if len(orders) != len(set(orders)):
        errors.append("stage order values must be unique")


def _validate_stage_contracts(
    stages: Mapping[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    for stage_name, stage_values in stages.items():
        values = _mapping(stage_values)
        output_fields = string_tuple(values.get("output_fields", ()))
        forbidden_output_fields = _find_forbidden_field_refs(output_fields)
        if forbidden_output_fields:
            errors.append(
                f"{stage_name} declares forbidden output fields: "
                f"{', '.join(forbidden_output_fields)}"
            )
        for ref in string_tuple(values.get("output_refs", ())):
            path_error = _generated_output_path_error(ref)
            if path_error:
                errors.append(path_error)
        if values.get("network_required") is True:
            errors.append(f"{stage_name} requires network access")
        if values.get("secrets_required") is True:
            errors.append(f"{stage_name} requires secrets")
        if not values.get("implementation_ref"):
            warnings.append(f"{stage_name} implementation_ref is unknown")


def _validate_feedback_edges(stages: Mapping[str, Any], errors: list[str]) -> None:
    backtest_outputs: set[str] = set()
    report_outputs: set[str] = set()
    for stage_name, stage_values in stages.items():
        values = _mapping(stage_values)
        outputs = set(string_tuple(values.get("output_refs", ())))
        outputs.update(string_tuple(values.get("output_fields", ())))
        if stage_name in STEP19_BACKTEST_STAGES:
            backtest_outputs.update(outputs)
        if stage_name in STEP19_REPORT_STAGES:
            report_outputs.update(outputs)

    for stage_name, stage_values in stages.items():
        values = _mapping(stage_values)
        inputs = set(string_tuple(values.get("input_refs", ())))
        inputs.update(string_tuple(values.get("input_fields", ())))
        return_fields = _find_return_feedback_refs(inputs)
        if stage_name in STEP19_UPSTREAM_STAGES and return_fields:
            errors.append(
                f"{stage_name} consumes return/evaluation fields upstream: "
                f"{', '.join(return_fields)}"
            )
        backtest_feedback = _matching_refs(inputs, backtest_outputs)
        if stage_name in STEP19_UPSTREAM_STAGES and backtest_feedback:
            errors.append(
                f"{stage_name} feeds Step 17 outputs back upstream: "
                f"{', '.join(backtest_feedback)}"
            )
        report_feedback = _matching_refs(inputs, report_outputs)
        if stage_name in STEP19_UPSTREAM_STAGES_BEFORE_REPORT and report_feedback:
            errors.append(
                f"{stage_name} feeds Step 16 report output back into scoring/ranking: "
                f"{', '.join(report_feedback)}"
            )


def _find_config_forbidden_fields(stages: Mapping[str, Any]) -> list[str]:
    found: set[str] = set()
    for stage_values in stages.values():
        values = _mapping(stage_values)
        found.update(_find_forbidden_field_refs(string_tuple(values.get("output_fields", ()))))
    return sorted(found)


def _find_forbidden_field_refs(values: Iterable[str]) -> list[str]:
    return _find_common_forbidden_field_refs(values, STEP19_FORBIDDEN_OUTPUT_FIELDS)


def _find_return_feedback_refs(values: Iterable[str]) -> list[str]:
    return _find_common_forbidden_field_refs(
        values,
        STEP19_RETURN_FEEDBACK_FIELDS,
        match_mode="exact_or_contains",
    )


def _matching_refs(inputs: Iterable[str], outputs: Iterable[str]) -> list[str]:
    matches: set[str] = set()
    normalized_outputs = tuple(
        (output, _normalize_path(output), _is_directory_ref(output)) for output in outputs
    )
    for input_ref in inputs:
        normalized_input = _normalize_path(input_ref)
        input_is_dir = _is_directory_ref(input_ref)
        for output_ref, normalized_output, output_is_dir in normalized_outputs:
            if not normalized_input or not normalized_output:
                continue
            if normalized_input == normalized_output:
                matches.add(input_ref)
            elif output_is_dir and normalized_input.startswith(f"{normalized_output.rstrip('/')}/"):
                matches.add(input_ref)
            elif input_is_dir and normalized_output.startswith(f"{normalized_input.rstrip('/')}/"):
                matches.add(output_ref)
    return sorted(matches)


def _is_directory_ref(value: str) -> bool:
    return str(value).strip().replace("\\", "/").endswith("/")


def _generated_output_path_error(path: str) -> str | None:
    normalized = _normalize_path(path)
    if not _looks_like_path(normalized):
        return None
    if normalized.startswith(STEP19_FORBIDDEN_OUTPUT_PATH_PREFIXES):
        return f"generated output path is in a forbidden data/cache/report area: {path}"
    if normalized.endswith("/"):
        if normalized.startswith(STEP19_GENERATED_OUTPUT_PREFIXES):
            return None
        if "/generated" in normalized:
            return f"generated output path must stay under an approved generated report root: {path}"
        return None
    if "/generated/" in normalized and not normalized.startswith(STEP19_GENERATED_OUTPUT_PREFIXES):
        return f"generated output path must stay under an approved generated report root: {path}"
    if normalized.endswith((".csv", ".json", ".jsonl", ".parquet", ".xlsx")):
        if not normalized.startswith(STEP19_GENERATED_OUTPUT_PREFIXES):
            return f"runtime output file must stay under reports/*/generated/: {path}"
    return None


def _normalize_path(path: str) -> str:
    value = str(path).strip().replace("\\", "/")
    is_dir = value.endswith("/")
    value = value.lstrip("./")
    try:
        value = str(PurePosixPath(value.rstrip("/")))
    except ValueError:
        pass
    value = value.lower()
    return f"{value}/" if is_dir and value else value


def _looks_like_path(value: str) -> bool:
    return "/" in value or "\\" in value or "." in PurePosixPath(value).name


def _is_forbidden_stage_name(stage_name: str) -> bool:
    normalized = stage_name.strip().lower()
    return any(token in normalized for token in STEP19_FORBIDDEN_STAGE_TOKENS)


def _is_allowed_negated_match(lowered: str, match: re.Match[str], _label: str) -> bool:
    prefix = lowered[max(0, match.start() - 48) : match.start()]
    return any(
        marker in prefix
        for marker in (
            "not a ",
            "not an ",
            "not ",
            "no ",
            "without ",
            "does not ",
            "do not ",
            "must not ",
            "forbidden ",
            "blocked ",
            "reject ",
            "rejected ",
            "inactive ",
            "disabled ",
            "candidate-only ",
        )
    )


def _assert_false_flag(values: Mapping[str, Any], name: str, errors: list[str]) -> None:
    if values.get(name) is True:
        errors.append(f"{name} must be false")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


__all__ = (
    "STEP19_CANONICAL_STAGE_ORDER",
    "STEP19_PIPELINE_NOTICE",
    "Step19PipelineGuardrailResult",
    "find_step19_forbidden_language",
    "find_step20_completion_claims",
    "validate_step19_generated_output_path",
    "validate_step19_pipeline_config",
    "validate_step19_pipeline_summary",
)
