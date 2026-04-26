from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY  # noqa: E402
from src.scanner.latest_ranking_policy import Step15RankingPolicy  # noqa: E402
from src.scanner.latest_ranking_validation import validate_step15_latest_ranking_output  # noqa: E402


def test_scanner_ranking_validator_accepts_explicit_non_korean_symbol_policy() -> None:
    frame = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "date": "2026-04-24",
                "rank": 1,
                "technical_composite_score": 2.0,
                "final_composite_score": 2.0,
                "coverage_metric": 1.0,
                "data_quality_flag": "valid",
                "warmup_status": "ready",
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 1,
                "expected_score_count": 1,
                "neutral_shrinkage_count": 0,
                "review_routed_score_count": 0,
                "final_score_policy": "technical_only_no_valuation",
                "technical_only_notice": "extension_contract_test_no_activation",
            },
            {
                "ticker": "MSFT",
                "date": "2026-04-24",
                "rank": 2,
                "technical_composite_score": 1.0,
                "final_composite_score": 1.0,
                "coverage_metric": 1.0,
                "data_quality_flag": "valid",
                "warmup_status": "ready",
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 1,
                "expected_score_count": 1,
                "neutral_shrinkage_count": 0,
                "review_routed_score_count": 0,
                "final_score_policy": "technical_only_no_valuation",
                "technical_only_notice": "extension_contract_test_no_activation",
            },
        ]
    )
    policy = Step15RankingPolicy(symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY)

    validate_step15_latest_ranking_output(frame, policy=policy)
