"""Step 9 Research Tester score contracts.

The contracts here are small metadata objects shared by Part A tests and score
code. They do not import Part B modules and do not activate scanner runtime.
"""

from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED_FOR_RESEARCH = "implemented_for_research"
NOT_IMPLEMENTED_MISSING_CONTRACT = "not_implemented_due_to_missing_contract"


@dataclass(frozen=True)
class ScoreImplementationContract:
    score_name: str
    raw_column: str
    score_family: str
    score_branch: str
    minimum_history: int
    implementation_status: str
    required_columns: tuple[str, ...]
    formula_note: str
    missing_contract_reason: str = ""

    @property
    def missing_reason_column(self) -> str:
        return f"{self.score_name}_missing_reason"


PART_A_SCORE_CONTRACTS: tuple[ScoreImplementationContract, ...] = (
    ScoreImplementationContract(
        score_name="short_term_overreaction",
        raw_column="short_term_overreaction_raw",
        score_family="mean_reversion",
        score_branch="technical",
        minimum_history=60,
        implementation_status=IMPLEMENTED_FOR_RESEARCH,
        required_columns=("ticker", "date", "close"),
        formula_note=(
            "MVP locked variant: negative configured short-window return, "
            "-return_N, using returns.short from Quant_mvp/config/windows.toml."
        ),
    ),
    ScoreImplementationContract(
        score_name="atr_adjusted_oversold_distance",
        raw_column="atr_adjusted_oversold_distance_raw",
        score_family="mean_reversion",
        score_branch="technical",
        minimum_history=60,
        implementation_status=IMPLEMENTED_FOR_RESEARCH,
        required_columns=("ticker", "date", "close", "atr_14", "bollinger_mid_20"),
        formula_note=(
            "MVP locked variant: (bollinger_mid_N - close) / ATR_M, using the "
            "configured Bollinger and ATR windows."
        ),
    ),
    ScoreImplementationContract(
        score_name="rsi_price_divergence",
        raw_column="rsi_price_divergence_raw",
        score_family="oscillator_divergence",
        score_branch="technical",
        minimum_history=90,
        implementation_status=IMPLEMENTED_FOR_RESEARCH,
        required_columns=("ticker", "date", "close", "rsi_14"),
        formula_note=(
            "MVP locked deterministic proxy: max(0, -return_N) * "
            "max(0, RSI_t - RSI_{t-N}), using returns.short as N."
        ),
    ),
    ScoreImplementationContract(
        score_name="realized_vol_percentile",
        raw_column="realized_vol_percentile_raw",
        score_family="volatility_regime",
        score_branch="diagnostic",
        minimum_history=120,
        implementation_status=IMPLEMENTED_FOR_RESEARCH,
        required_columns=("ticker", "date", "realized_vol_20"),
        formula_note=(
            "Trailing percentile of realized_vol_20 within ticker-local current/prior "
            "observations. Diagnostic context only."
        ),
    ),
)

PART_A_RAW_COLUMNS = tuple(contract.raw_column for contract in PART_A_SCORE_CONTRACTS)
PART_A_MISSING_REASON_COLUMNS = tuple(
    contract.missing_reason_column for contract in PART_A_SCORE_CONTRACTS
)
PART_A_SCORE_NAMES = tuple(contract.score_name for contract in PART_A_SCORE_CONTRACTS)


def part_a_contract_by_name(score_name: str) -> ScoreImplementationContract:
    for contract in PART_A_SCORE_CONTRACTS:
        if contract.score_name == score_name:
            return contract
    raise KeyError(f"Unknown Step 9 Part A score: {score_name}")
