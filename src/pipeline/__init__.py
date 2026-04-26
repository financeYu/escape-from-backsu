"""Step 19 automatic execution pipeline package."""

from src.pipeline.contracts import (
    PipelineRunMode,
    PipelineRunSummary,
    PipelineStageContract,
    PipelineStageResult,
    PipelineStageStatus,
)
from src.pipeline.step19_pipeline import (
    DEFAULT_STEP19_PIPELINE_CONFIG,
    build_default_stage_contracts,
    load_pipeline_config,
    run_step19_pipeline,
)

__all__ = (
    "DEFAULT_STEP19_PIPELINE_CONFIG",
    "PipelineRunMode",
    "PipelineRunSummary",
    "PipelineStageContract",
    "PipelineStageResult",
    "PipelineStageStatus",
    "build_default_stage_contracts",
    "load_pipeline_config",
    "run_step19_pipeline",
)
