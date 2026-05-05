"""Shared v0.3 ML label policy constants.

These values keep candidate-level actual labels separated from generic proxy
metrics across EvaluationEvidence generation and ML-ready row building.
"""

GENERIC_PROXY_LABEL_STATUS = "generic_momentum_proxy_not_supervised"
GENERIC_PROXY_LABEL_ROLE = "generic_momentum_proxy"
GENERIC_PROXY_LIMITATION = "shared_strategy_rule_fingerprint_not_candidate_specific_label"
GENERIC_PROXY_BLOCKED_REASON = "generic_momentum_proxy_not_candidate_level"
GENERIC_PROXY_REVIEW_NOTE = (
    "metric_summary is a shared generic momentum proxy and must not be used "
    "as a candidate-level supervised label"
)

