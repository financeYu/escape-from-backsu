"""KIS revision data snapshot schema drafts for v1.4 diagnostics.

This module is intentionally storage-only. It does not call KIS APIs and it
does not promote revision fields into any feature allowlist.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from stock_core.utils.local_env import check_local_env_presence
from stock_core.utils.paths import PROJECT_ROOT


KIS_PROVIDER = "kis_open_api"

KIS_REQUIRED_ENV_VARS = (
    "KIS_APP_KEY",
    "KIS_APP_SECRET",
    "KIS_ACCESS_TOKEN",
)

RAW_SNAPSHOT_REQUIRED_FIELDS = (
    "provider",
    "endpoint_name",
    "code",
    "collected_at",
    "request_date",
    "raw_json",
    "raw_hash",
    "source_ref",
)

KIS_REVISION_ENDPOINTS: dict[str, dict[str, Any]] = {
    "estimate_perform": {
        "display_name": "국내주식 종목추정실적",
        "api_path": "/uapi/domestic-stock/v1/quotations/estimate-perform",
        "tr_id": "HHKST668300C0",
        "request_fields": ("SHT_CD",),
        "response_sections": ("output1", "output2", "output3", "output4"),
        "observed_response_fields": (
            "sht_cd",
            "item_kor_nm",
            "estdate",
            "capital",
            "forn_item_lmtrt",
            "data1",
            "data2",
            "data3",
            "data4",
            "data5",
            "dt",
        ),
        "source_ref": (
            "https://github.com/koreainvestment/open-trading-api/tree/main/"
            "examples_llm/domestic_stock/estimate_perform"
        ),
        "pit_available_at_rule": "use_collected_at_until_response_date_semantics_verified",
    },
    "invest_opinion": {
        "display_name": "국내주식 종목투자의견",
        "api_path": "/uapi/domestic-stock/v1/quotations/invest-opinion",
        "tr_id": "FHKST663300C0",
        "request_fields": (
            "FID_COND_MRKT_DIV_CODE",
            "FID_COND_SCR_DIV_CODE",
            "FID_INPUT_ISCD",
            "FID_INPUT_DATE_1",
            "FID_INPUT_DATE_2",
        ),
        "response_sections": ("output",),
        "observed_response_fields": (
            "stck_bsop_date",
            "invt_opnn",
            "invt_opnn_cls_code",
            "rgbf_invt_opnn",
            "rgbf_invt_opnn_cls_code",
            "hts_goal_prc",
            "stck_prdy_clpr",
            "stck_nday_esdg",
            "nday_dprt",
            "stft_esdg",
            "dprt",
        ),
        "source_ref": (
            "https://github.com/koreainvestment/open-trading-api/tree/main/"
            "examples_llm/domestic_stock/invest_opinion"
        ),
        "pit_available_at_rule": "use_stck_bsop_date_if_verified_else_collected_at",
    },
    "invest_opbysec": {
        "display_name": "국내주식 증권사별 투자의견",
        "api_path": "/uapi/domestic-stock/v1/quotations/invest-opbysec",
        "tr_id": "FHKST663400C0",
        "request_fields": (
            "FID_COND_MRKT_DIV_CODE",
            "FID_COND_SCR_DIV_CODE",
            "FID_INPUT_ISCD",
            "FID_DIV_CLS_CODE",
            "FID_INPUT_DATE_1",
            "FID_INPUT_DATE_2",
        ),
        "response_sections": ("output",),
        "observed_response_fields": (
            "stck_bsop_date",
            "stck_shrn_iscd",
            "hts_kor_isnm",
            "invt_opnn",
            "invt_opnn_cls_code",
            "rgbf_invt_opnn",
            "rgbf_invt_opnn_cls_code",
            "stck_prpr",
            "prdy_vrss",
            "prdy_vrss_sign",
            "prdy_ctrt",
            "hts_goal_prc",
            "stck_prdy_clpr",
            "stft_esdg",
            "dprt",
        ),
        "source_ref": (
            "https://github.com/koreainvestment/open-trading-api/tree/main/"
            "examples_llm/domestic_stock/invest_opbysec"
        ),
        "pit_available_at_rule": "use_stck_bsop_date_if_verified_else_collected_at",
    },
}

NORMALIZED_CONSENSUS_SCHEMA_DRAFT: tuple[dict[str, str], ...] = (
    {"name": "provider", "type": "string", "rule": "source provider id"},
    {"name": "endpoint_name", "type": "string", "rule": "KIS endpoint key"},
    {"name": "code", "type": "string", "rule": "Korean equity short code"},
    {"name": "collected_at", "type": "datetime", "rule": "UTC collector timestamp"},
    {"name": "request_date", "type": "string", "rule": "collector request date or range key"},
    {
        "name": "available_at",
        "type": "datetime|null",
        "rule": "verified response base date if clear, otherwise collected_at",
    },
    {
        "name": "source_date_field",
        "type": "string|null",
        "rule": "raw response field used for available_at, never fiscal period",
    },
    {"name": "fiscal_period", "type": "string|null", "rule": "target fiscal period only"},
    {"name": "metric_name", "type": "string|null", "rule": "normalized consensus metric"},
    {"name": "metric_value", "type": "number|string|null", "rule": "raw-preserving normalized value"},
    {"name": "broker_or_member_code", "type": "string|null", "rule": "member code if endpoint provides it"},
    {"name": "opinion_code", "type": "string|null", "rule": "raw opinion class code if provided"},
    {"name": "previous_opinion_code", "type": "string|null", "rule": "raw previous opinion class code"},
    {"name": "raw_hash", "type": "string", "rule": "sha256 of canonical raw_json"},
    {"name": "source_ref", "type": "string", "rule": "doc or endpoint reference"},
    {"name": "feature_allowlist_state", "type": "string", "rule": "blocked_candidate_only"},
)

BLOCKED_UNTIL_HISTORY_AVAILABLE_MANIFEST: dict[str, Any] = {
    "status": "blocked_candidate_only",
    "blocked_reason": "PIT-safe historical consensus snapshots are not yet collected.",
    "usable_for_v1_4_feature_manifest": False,
    "auto_reference_allowed": False,
    "downstream_consumption_policy": (
        "raw_snapshots_may_accumulate_but_must_not_feed_v1_4_features_scores_"
        "rankings_or_incremental_evidence_until_explicit_pit_promotion"
    ),
    "blocked_features": (
        "eps_estimate_1m_ago",
        "eps_estimate_3m_ago",
        "analyst_revision_up_count_1m",
        "analyst_revision_down_count_1m",
        "sector_revision_percentile",
    ),
    "unlock_requirements": (
        "daily_or_periodic_raw_snapshots_with_collected_at",
        "verified_available_at_mapping_per_endpoint",
        "stable_ticker_to_sector_taxonomy_lineage",
        "history_window_covering_at_least_3_months",
        "no_feature_allowlist_promotion_before_pit_validation",
    ),
}


@dataclass(frozen=True)
class KisApiKeyConfig:
    """Secret-safe KIS credential presence loaded from the local key store."""

    app_key_present: bool
    app_secret_present: bool
    access_token_present: bool
    checked_env_vars: tuple[str, ...] = KIS_REQUIRED_ENV_VARS
    source_paths: tuple[Path, ...] = ()
    attempted_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class KisApiKeyReadiness:
    """Secret-safe readiness result for later KIS raw snapshot collection."""

    status: str
    missing_materials: tuple[str, ...]
    warnings: tuple[str, ...]
    config_summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["missing_materials"] = list(self.missing_materials)
        data["warnings"] = list(self.warnings)
        return data


def load_kis_api_key_config(
    env: MutableMapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> KisApiKeyConfig:
    """Load KIS credential presence from api_management without exposing values."""

    source = os.environ if env is None else env
    presence = check_local_env_presence(
        KIS_REQUIRED_ENV_VARS,
        project_root=project_root,
        environ=source,
    )
    return KisApiKeyConfig(
        app_key_present=_secret_present(source.get("KIS_APP_KEY")),
        app_secret_present=_secret_present(source.get("KIS_APP_SECRET")),
        access_token_present=_secret_present(source.get("KIS_ACCESS_TOKEN")),
        source_paths=presence.source_paths,
        attempted_paths=presence.attempted_paths,
    )


def check_kis_api_key_readiness(config: KisApiKeyConfig) -> KisApiKeyReadiness:
    missing = []
    if not config.app_key_present:
        missing.append("KIS_APP_KEY")
    if not config.app_secret_present:
        missing.append("KIS_APP_SECRET")
    if not config.access_token_present:
        missing.append("KIS_ACCESS_TOKEN")

    summary: dict[str, object] = {
        "app_key_present": config.app_key_present,
        "app_secret_present": config.app_secret_present,
        "access_token_present": config.access_token_present,
        "checked_env_vars": list(config.checked_env_vars),
        "source_paths": [str(path) for path in config.source_paths],
        "attempted_paths": [str(path) for path in config.attempted_paths],
        "secret_values_redacted": True,
    }
    return KisApiKeyReadiness(
        status="ready" if not missing else "blocked",
        missing_materials=tuple(missing),
        warnings=(),
        config_summary=summary,
    )

def _secret_present(value: str | None) -> bool:
    return bool(value and value.strip())


def canonical_raw_json(raw_json: Any) -> str:
    """Return stable JSON text for raw KIS payload hashing."""

    return json.dumps(raw_json, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_raw_hash(raw_json: Any) -> str:
    """Compute the canonical SHA-256 hash for a raw payload."""

    return hashlib.sha256(canonical_raw_json(raw_json).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_raw_snapshot_record(
    *,
    endpoint_name: str,
    code: str,
    request_date: str,
    raw_json: Any,
    source_ref: str,
    collected_at: str | None = None,
    provider: str = KIS_PROVIDER,
) -> dict[str, Any]:
    """Build a PIT-safe raw snapshot record without normalizing feature values."""

    if endpoint_name not in KIS_REVISION_ENDPOINTS:
        raise ValueError(f"unsupported KIS revision endpoint: {endpoint_name}")
    if not code:
        raise ValueError("code is required")
    if not request_date:
        raise ValueError("request_date is required")
    if not source_ref:
        raise ValueError("source_ref is required")

    record: dict[str, Any] = {
        "provider": provider,
        "endpoint_name": endpoint_name,
        "code": code,
        "collected_at": collected_at or utc_now_iso(),
        "request_date": request_date,
        "raw_json": raw_json,
        "raw_hash": compute_raw_hash(raw_json),
        "source_ref": source_ref,
    }
    validate_raw_snapshot_record(record)
    return record


def validate_raw_snapshot_record(record: Mapping[str, Any]) -> None:
    missing = [field for field in RAW_SNAPSHOT_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"missing raw snapshot fields: {missing}")
    if record["raw_hash"] != compute_raw_hash(record["raw_json"]):
        raise ValueError("raw_hash does not match raw_json")
