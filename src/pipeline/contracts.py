"""Contracts for the Step 19 automatic execution pipeline.

The Step 19 pipeline is an orchestration layer. These contracts describe stage
boundaries and run summaries without changing Step 15 ranking, Step 16 report,
Step 17 backtest, or Step 18 valuation/fundamental semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PipelineStageStatus(str, Enum):
    """Lifecycle values for a pipeline stage."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"


class PipelineRunMode(str, Enum):
    """Supported Step 19 run modes."""

    DRY_RUN = "dry_run"
    VALIDATE_ONLY = "validate_only"
    RUN_ALLOWED_STAGES = "run_allowed_stages"


@dataclass(frozen=True)
class PipelineStageContract:
    """Declarative contract for one Step 19 orchestration stage."""

    stage_name: str
    order: int
    enabled: bool = True
    optional: bool = False
    input_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    read_only_upstream_context: tuple[str, ...] = ()
    forbidden_inputs: tuple[str, ...] = ()
    allowed_generated_outputs: tuple[str, ...] = ()
    validation_expectations: tuple[str, ...] = ()
    required_input_paths: tuple[str, ...] = ()
    implementation_ref: str = "unknown"
    execution_policy: str = "contract_validation_only"
    boundary_notes: tuple[str, ...] = ()

    @classmethod
    def from_mapping(
        cls,
        stage_name: str,
        values: dict[str, Any],
        *,
        order: int,
    ) -> "PipelineStageContract":
        """Build a contract from parsed config values."""

        def _tuple_value(name: str) -> tuple[str, ...]:
            value = values.get(name, ())
            if value is None:
                return ()
            if isinstance(value, str):
                return (value,)
            return tuple(str(item) for item in value)

        return cls(
            stage_name=stage_name,
            order=int(values.get("order", order)),
            enabled=bool(values.get("enabled", True)),
            optional=bool(values.get("optional", False)),
            input_refs=_tuple_value("input_refs"),
            output_refs=_tuple_value("output_refs"),
            read_only_upstream_context=_tuple_value("read_only_upstream_context"),
            forbidden_inputs=_tuple_value("forbidden_inputs"),
            allowed_generated_outputs=_tuple_value("allowed_generated_outputs"),
            validation_expectations=_tuple_value("validation_expectations"),
            required_input_paths=_tuple_value("required_input_paths"),
            implementation_ref=str(values.get("implementation_ref", "unknown")),
            execution_policy=str(
                values.get("execution_policy", "contract_validation_only")
            ),
            boundary_notes=_tuple_value("boundary_notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable contract shape."""

        return {
            "stage_name": self.stage_name,
            "order": self.order,
            "enabled": self.enabled,
            "optional": self.optional,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "read_only_upstream_context": list(self.read_only_upstream_context),
            "forbidden_inputs": list(self.forbidden_inputs),
            "allowed_generated_outputs": list(self.allowed_generated_outputs),
            "validation_expectations": list(self.validation_expectations),
            "required_input_paths": list(self.required_input_paths),
            "implementation_ref": self.implementation_ref,
            "execution_policy": self.execution_policy,
            "boundary_notes": list(self.boundary_notes),
        }


@dataclass(frozen=True)
class PipelineStageResult:
    """Result for one Step 19 pipeline stage."""

    stage_name: str
    status: PipelineStageStatus
    input_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    boundary_notes: tuple[str, ...] = ()
    validation_status: str = "not_run"

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable result shape."""

        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "boundary_notes": list(self.boundary_notes),
            "validation_status": self.validation_status,
        }


@dataclass(frozen=True)
class PipelineRunSummary:
    """Structured summary for one Step 19 pipeline run."""

    run_mode: PipelineRunMode
    generated_at: str
    stages: tuple[PipelineStageResult, ...]
    overall_status: PipelineStageStatus
    validation_summary: dict[str, Any]
    forbidden_scope_check: dict[str, Any]
    no_semantics_changed_notice: str
    selected_stages: tuple[str, ...] = ()
    skipped_stages: tuple[str, ...] = ()
    git_commit: str = "unknown"
    boundary_notice: str = (
        "Step 19 orchestrates approved stages only; it does not redefine "
        "scores, ranking, reports, backtests, or valuation/fundamental scoring."
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serializable summary shape."""

        return {
            "run_mode": self.run_mode.value,
            "generated_at": self.generated_at,
            "git_commit": self.git_commit,
            "selected_stages": list(self.selected_stages),
            "skipped_stages": list(self.skipped_stages),
            "stages": [stage.to_dict() for stage in self.stages],
            "overall_status": self.overall_status.value,
            "validation_summary": self.validation_summary,
            "forbidden_scope_check": self.forbidden_scope_check,
            "no_semantics_changed_notice": self.no_semantics_changed_notice,
            "boundary_notice": self.boundary_notice,
        }


__all__ = (
    "PipelineRunMode",
    "PipelineRunSummary",
    "PipelineStageContract",
    "PipelineStageResult",
    "PipelineStageStatus",
)
