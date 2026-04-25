"""Step 11 composite schema boundary.

This package exposes validation contracts only. It does not calculate
composite scores, rankings, signals, valuation scores, forward returns, or
backtest labels.
"""

from .contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    DEFAULT_STATUS_PROPAGATION_CONTRACT,
    DIRECT_CANDIDATE_SCORE_NAMES,
    MVP_SCORE_NAMES,
    CompositeEligibility,
    CompositeInputSpec,
    CompositeRole,
    NormalizationScope,
    StatusPropagationContract,
)
from .schema import (
    assert_no_forbidden_step11_output_columns,
    assert_ticker_date_identity_unchanged,
    candidate_signal_specs,
    find_forbidden_step11_output_columns,
    validate_composite_input_registry,
    validate_normalized_score_columns,
    validate_step11_config_flags,
)

__all__ = (
    "DEFAULT_COMPOSITE_INPUT_REGISTRY",
    "DEFAULT_STATUS_PROPAGATION_CONTRACT",
    "DIRECT_CANDIDATE_SCORE_NAMES",
    "MVP_SCORE_NAMES",
    "CompositeEligibility",
    "CompositeInputSpec",
    "CompositeRole",
    "NormalizationScope",
    "StatusPropagationContract",
    "assert_no_forbidden_step11_output_columns",
    "assert_ticker_date_identity_unchanged",
    "candidate_signal_specs",
    "find_forbidden_step11_output_columns",
    "validate_composite_input_registry",
    "validate_normalized_score_columns",
    "validate_step11_config_flags",
)
