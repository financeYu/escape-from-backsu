"""Market, universe, symbol, and provider policy objects.

The current runtime defaults remain the KOSPI200 universe and Naver Finance
daily-price provider. These specs make those assumptions explicit so future
market support can add new policies without changing core scanner logic first.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SymbolPolicy:
    """Normalization and validation rules for instrument identifiers."""

    policy_id: str
    normalize_numeric_width: int | None
    valid_pattern: str
    compact_alphanumeric: bool = True
    extract_pattern: str | None = None

    def normalize(self, value: object) -> str:
        raw = str(value).strip().upper()
        normalized = raw
        if normalized.isdigit() and self.normalize_numeric_width is not None:
            return normalized.zfill(self.normalize_numeric_width)

        if self.compact_alphanumeric:
            compact = "".join(character for character in normalized if character.isalnum())
            if compact:
                normalized = compact

        if self.is_valid(normalized):
            return normalized

        if self.extract_pattern:
            match = re.search(self.extract_pattern, raw)
            if match:
                extracted = match.group(1).upper()
                if extracted.isdigit() and self.normalize_numeric_width is not None:
                    return extracted.zfill(self.normalize_numeric_width)
                return extracted

        return normalized

    def is_valid(self, value: object) -> bool:
        return bool(re.fullmatch(self.valid_pattern, str(value).strip().upper()))

    def leading_zero_loss_candidates(self, values) -> int:
        if self.normalize_numeric_width is None:
            return 0
        ticker_text = values.astype(str).str.strip()
        non_null = values.notna()
        short_digit_tickers = non_null & ticker_text.str.isdigit() & (ticker_text.str.len() < self.normalize_numeric_width)
        if not short_digit_tickers.any():
            return 0
        return int(short_digit_tickers.sum())


@dataclass(frozen=True)
class UniverseSpec:
    """Declarative CSV universe contract."""

    universe_id: str
    display_name: str
    packaged_filename: str
    snapshot_filename: str
    symbol_policy: SymbolPolicy
    expected_size: int | None = None
    live_refresh_supported: bool = False

    def validate_size(self, size: int) -> None:
        if self.expected_size is None:
            return
        if size != self.expected_size:
            raise ValueError(
                f"{self.display_name} universe file must contain exactly "
                f"{self.expected_size} unique instruments, found {size}"
            )


@dataclass(frozen=True)
class PriceProviderSpec:
    """Runtime assumptions owned by a daily price provider."""

    provider_id: str
    display_name: str
    data_vendor: str
    rows_per_page: int
    request_sleep_seconds: float = 0.3


KOREAN_EQUITY_SYMBOL_POLICY = SymbolPolicy(
    policy_id="korean_equity_6",
    normalize_numeric_width=6,
    valid_pattern=r"^[0-9A-Z]{6}$",
    extract_pattern=r"([A-Z0-9]+)",
)

GENERIC_EXCHANGE_SYMBOL_POLICY = SymbolPolicy(
    policy_id="generic_exchange_symbol",
    normalize_numeric_width=None,
    valid_pattern=r"^[0-9A-Z][0-9A-Z._-]{0,31}$",
    compact_alphanumeric=False,
)

KOSPI200_UNIVERSE_SPEC = UniverseSpec(
    universe_id="kospi200",
    display_name="KOSPI200",
    packaged_filename="kospi200.csv",
    snapshot_filename="kospi200_snapshot.csv",
    symbol_policy=KOREAN_EQUITY_SYMBOL_POLICY,
    expected_size=200,
    live_refresh_supported=False,
)

NAVER_PRICE_PROVIDER_SPEC = PriceProviderSpec(
    provider_id="naver_finance",
    display_name="Naver Finance",
    data_vendor="naver_finance",
    rows_per_page=10,
    request_sleep_seconds=0.3,
)
