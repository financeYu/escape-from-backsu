"""Step 12 score redundancy and correlation diagnostics.

This public module preserves the historical ``src.diagnostics.score_redundancy``
API while the implementation lives in smaller responsibility-focused modules.
The diagnostics remain review material only: they do not create rankings,
composite scores, signals, valuation fields, forward-return labels, or backtest
outputs.
"""

from __future__ import annotations

from .score_redundancy_config import (
    ScoreRedundancyConfig,
    ScoreRedundancyConfigError,
    load_score_redundancy_config,
)
from .score_redundancy_contract_adapter import build_score_redundancy_diagnostics
from .score_redundancy_engine import (
    PAIR_DATE_COLUMNS,
    PAIR_SUMMARY_COLUMNS,
    calculate_score_pair_correlations,
    summarize_score_redundancy,
)
from .score_redundancy_inputs import (
    RedundancyScoreInput,
    prepare_redundancy_input_frame,
    score_inputs_from_columns,
    score_inputs_from_registry,
)


__all__ = (
    "PAIR_DATE_COLUMNS",
    "PAIR_SUMMARY_COLUMNS",
    "RedundancyScoreInput",
    "ScoreRedundancyConfig",
    "ScoreRedundancyConfigError",
    "build_score_redundancy_diagnostics",
    "calculate_score_pair_correlations",
    "load_score_redundancy_config",
    "prepare_redundancy_input_frame",
    "score_inputs_from_columns",
    "score_inputs_from_registry",
    "summarize_score_redundancy",
)
