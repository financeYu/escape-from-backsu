"""v1.0-rc HorizonPolicy loader and validator.

The policy is an evidence-only planning contract. It separates label,
simulation, holding-period, entry-lag, signal-frequency, rebalance, and
calendar assumptions so next-day / 1D behavior is explicit instead of hidden
inside call sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HORIZON_POLICY_CONFIG = PROJECT_ROOT / "config" / "horizon_policy.toml"
DEFAULT_HORIZON_ID = "1d"
SUPPORTED_HORIZON_IDS = frozenset({"1d", "5d", "20d", "1w", "1m"})
ALLOWED_SIGNAL_FREQUENCIES = frozenset({"daily", "weekly", "monthly"})
ALLOWED_REBALANCE_FREQUENCIES = frozenset({"daily", "weekly", "monthly", "none"})
ALLOWED_CALENDAR_POLICIES = frozenset({"trading_days"})


@dataclass(frozen=True)
class HorizonPolicy:
    """Resolved v1.0-rc horizon contract."""

    horizon_id: str
    signal_frequency: str
    entry_lag_trading_days: int
    holding_period_trading_days: int
    rebalance_frequency: str
    label_horizon: str
    simulation_horizon: str
    calendar_policy: str
    rebalance_disclosure_required: bool = True
    compatibility_note: str = ""
    defaulted: bool = False
    default_reason: str = ""

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, Any],
        *,
        defaulted: bool = False,
        default_reason: str = "",
    ) -> "HorizonPolicy":
        required = (
            "horizon_id",
            "signal_frequency",
            "entry_lag_trading_days",
            "holding_period_trading_days",
            "rebalance_frequency",
            "label_horizon",
            "simulation_horizon",
            "calendar_policy",
        )
        missing = [field for field in required if field not in values]
        if missing:
            raise ValueError(f"HorizonPolicy missing required fields: {', '.join(missing)}")
        policy = cls(
            horizon_id=str(values["horizon_id"]).strip().lower(),
            signal_frequency=str(values["signal_frequency"]).strip().lower(),
            entry_lag_trading_days=_positive_int(values["entry_lag_trading_days"], "entry_lag_trading_days"),
            holding_period_trading_days=_positive_int(
                values["holding_period_trading_days"],
                "holding_period_trading_days",
            ),
            rebalance_frequency=str(values["rebalance_frequency"]).strip().lower(),
            label_horizon=str(values["label_horizon"]).strip().lower(),
            simulation_horizon=str(values["simulation_horizon"]).strip().lower(),
            calendar_policy=str(values["calendar_policy"]).strip().lower(),
            rebalance_disclosure_required=bool(values.get("rebalance_disclosure_required", True)),
            compatibility_note=str(values.get("compatibility_note") or ""),
            defaulted=defaulted,
            default_reason=default_reason,
        )
        validate_horizon_policy(policy)
        return policy

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizon_id": self.horizon_id,
            "signal_frequency": self.signal_frequency,
            "entry_lag_trading_days": self.entry_lag_trading_days,
            "holding_period_trading_days": self.holding_period_trading_days,
            "rebalance_frequency": self.rebalance_frequency,
            "label_horizon": self.label_horizon,
            "simulation_horizon": self.simulation_horizon,
            "calendar_policy": self.calendar_policy,
            "rebalance_disclosure_required": self.rebalance_disclosure_required,
            "compatibility_note": self.compatibility_note,
            "defaulted": self.defaulted,
            "default_reason": self.default_reason,
        }


def load_horizon_policy_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the HorizonPolicy TOML payload."""

    path = Path(config_path) if config_path is not None else DEFAULT_HORIZON_POLICY_CONFIG
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if "horizon_policy" not in payload:
        raise ValueError("HorizonPolicy config must define [[horizon_policy]] entries")
    return payload


def resolve_horizon_policy(
    horizon_id: str | None = None,
    *,
    config_path: str | Path | None = None,
) -> HorizonPolicy:
    """Resolve a policy by ID, defaulting visibly to 1d when omitted."""

    payload = load_horizon_policy_config(config_path)
    defaults = payload.get("defaults", {})
    selected_id = str(horizon_id or defaults.get("default_horizon_id") or DEFAULT_HORIZON_ID).strip().lower()
    defaulted = horizon_id is None
    policies = {
        str(entry.get("horizon_id", "")).strip().lower(): entry
        for entry in payload.get("horizon_policy", [])
        if isinstance(entry, Mapping)
    }
    if selected_id not in policies:
        raise ValueError(f"unknown HorizonPolicy horizon_id: {selected_id}")
    return HorizonPolicy.from_mapping(
        policies[selected_id],
        defaulted=defaulted,
        default_reason=str(defaults.get("default_reason") or "") if defaulted else "",
    )


def validate_horizon_policy(policy: HorizonPolicy) -> None:
    """Validate a resolved policy and reject unsupported horizon semantics."""

    if policy.horizon_id not in SUPPORTED_HORIZON_IDS:
        raise ValueError(f"unsupported HorizonPolicy horizon_id: {policy.horizon_id}")
    if policy.signal_frequency not in ALLOWED_SIGNAL_FREQUENCIES:
        raise ValueError(f"unsupported signal_frequency: {policy.signal_frequency}")
    if policy.rebalance_frequency not in ALLOWED_REBALANCE_FREQUENCIES:
        raise ValueError(f"unsupported rebalance_frequency: {policy.rebalance_frequency}")
    if policy.calendar_policy not in ALLOWED_CALENDAR_POLICIES:
        raise ValueError(f"unsupported calendar_policy: {policy.calendar_policy}")
    if policy.label_horizon not in SUPPORTED_HORIZON_IDS:
        raise ValueError(f"unsupported label_horizon: {policy.label_horizon}")
    if policy.simulation_horizon not in SUPPORTED_HORIZON_IDS:
        raise ValueError(f"unsupported simulation_horizon: {policy.simulation_horizon}")


def _positive_int(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if number < 1:
        raise ValueError(f"{field_name} must be at least 1")
    return number


__all__ = (
    "DEFAULT_HORIZON_ID",
    "DEFAULT_HORIZON_POLICY_CONFIG",
    "HorizonPolicy",
    "SUPPORTED_HORIZON_IDS",
    "load_horizon_policy_config",
    "resolve_horizon_policy",
    "validate_horizon_policy",
)
