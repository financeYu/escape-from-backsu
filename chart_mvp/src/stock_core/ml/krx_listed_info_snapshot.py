"""KRX listed-info raw snapshot helpers for v1.4 data supplements.

The public KRX listed-info API can supplement stock-code, ISIN, market, and
company mapping lineage. It does not provide analyst revision history and must
not unlock sector-relative revision features by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from stock_core.ml.kis_revision_snapshot_schema import RAW_SNAPSHOT_REQUIRED_FIELDS, compute_raw_hash, utc_now_iso
from stock_core.utils.local_env import check_local_env_presence, load_local_env_for_project
from stock_core.utils.paths import DATA_DIR, PROJECT_ROOT


KRX_LISTED_INFO_PROVIDER = "data_go_kr_krx"
KRX_LISTED_INFO_ENDPOINT_NAME = "krx_listed_info"
KRX_LISTED_INFO_API_KEY_ENV_VARS = (
    "DATA_GO_KR_API_KEY",
    "KRX_LISTED_INFO_API_KEY",
    "KRX_SERVICE_KEY",
)
KRX_LISTED_INFO_URL = "https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo"
KRX_LISTED_INFO_SOURCE_REF = "https://www.data.go.kr/data/15094775/openapi.do"
DEFAULT_KRX_LISTED_INFO_SNAPSHOT_DIR = DATA_DIR / "krx_listed_info_raw_snapshots"
DEFAULT_KRX_LISTED_INFO_PAGE_COUNT = 5000
DEFAULT_KRX_LISTED_INFO_CODE_PAGE_COUNT = 1

JsonGet = Callable[[str, Mapping[str, str], int], dict[str, Any]]


@dataclass(frozen=True)
class KrxListedInfoApiKeyConfig:
    api_key_present: bool
    selected_env_var: str | None
    checked_env_vars: tuple[str, ...] = KRX_LISTED_INFO_API_KEY_ENV_VARS
    source_paths: tuple[Path, ...] = ()
    attempted_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class KrxListedInfoApiKeyReadiness:
    status: str
    missing_materials: tuple[str, ...]
    config_summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["missing_materials"] = list(self.missing_materials)
        return data


@dataclass(frozen=True)
class KrxListedInfoSnapshotResult:
    output_path: Path
    records_written: int
    total_count: int | None
    pages_collected: int
    selected_env_var: str | None
    codes_requested: int = 0
    query_mode: str = "all_history_page"

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "records_written": self.records_written,
            "total_count": self.total_count,
            "pages_collected": self.pages_collected,
            "selected_env_var": self.selected_env_var,
            "codes_requested": self.codes_requested,
            "query_mode": self.query_mode,
            "secret_values_redacted": True,
        }


def load_krx_listed_info_api_key_config(
    env: MutableMapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> KrxListedInfoApiKeyConfig:
    source = os.environ if env is None else env
    presence = check_local_env_presence(
        KRX_LISTED_INFO_API_KEY_ENV_VARS,
        project_root=project_root,
        environ=source,
    )
    selected_env_var = _select_api_key_env_var(source)
    return KrxListedInfoApiKeyConfig(
        api_key_present=selected_env_var is not None,
        selected_env_var=selected_env_var,
        source_paths=presence.source_paths,
        attempted_paths=presence.attempted_paths,
    )


def check_krx_listed_info_api_key_readiness(
    config: KrxListedInfoApiKeyConfig,
) -> KrxListedInfoApiKeyReadiness:
    missing = () if config.api_key_present else ("DATA_GO_KR_API_KEY_OR_KRX_LISTED_INFO_API_KEY",)
    return KrxListedInfoApiKeyReadiness(
        status="ready" if not missing else "blocked",
        missing_materials=missing,
        config_summary={
            "api_key_present": config.api_key_present,
            "selected_env_var": config.selected_env_var,
            "checked_env_vars": list(config.checked_env_vars),
            "source_paths": [str(path) for path in config.source_paths],
            "attempted_paths": [str(path) for path in config.attempted_paths],
            "secret_values_redacted": True,
        },
    )


def collect_krx_listed_info_raw_snapshots(
    *,
    codes: Iterable[str] | None = None,
    output_dir: Path = DEFAULT_KRX_LISTED_INFO_SNAPSHOT_DIR,
    output_path: Path | None = None,
    page_count: int = DEFAULT_KRX_LISTED_INFO_PAGE_COUNT,
    max_pages: int = 1,
    env: MutableMapping[str, str] | None = None,
    project_root: Path = PROJECT_ROOT,
    timeout_seconds: int = 20,
    get_json: JsonGet | None = None,
) -> KrxListedInfoSnapshotResult:
    source = os.environ if env is None else env
    load_local_env_for_project(project_root, source)
    selected_env_var = _select_api_key_env_var(source)
    if selected_env_var is None:
        raise RuntimeError("KRX listed-info API key is not ready: missing DATA_GO_KR_API_KEY")
    api_key = source[selected_env_var].strip()
    if page_count < 1:
        raise ValueError("page_count must be at least 1")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    if codes is not None:
        normalized_codes = _normalize_codes(codes)
        return _collect_code_supplement_snapshots(
            codes=normalized_codes,
            api_key=api_key,
            selected_env_var=selected_env_var,
            output_dir=output_dir,
            output_path=output_path,
            timeout_seconds=timeout_seconds,
            get_json=get_json,
        )

    output_path = output_path or _default_snapshot_output_path(output_dir)
    requester = get_json or _get_json
    records_written = 0
    total_count: int | None = None
    pages_collected = 0

    for page_no in range(1, max_pages + 1):
        raw_json = fetch_krx_listed_info_page(
            api_key=api_key,
            page_no=page_no,
            page_count=page_count,
            timeout_seconds=timeout_seconds,
            get_json=requester,
        )
        body = _response_body(raw_json)
        total_count = _safe_int(body.get("totalCount"), default=total_count)
        record = build_krx_listed_info_raw_snapshot_record(
            request_date=utc_now_iso()[:10],
            raw_json=_with_request_context(raw_json, page_no=page_no, page_count=page_count),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            _write_record(handle, record)
        records_written += 1
        pages_collected += 1
        if total_count is not None and page_no * page_count >= total_count:
            break

    return KrxListedInfoSnapshotResult(
        output_path=output_path,
        records_written=records_written,
        total_count=total_count,
        pages_collected=pages_collected,
        selected_env_var=selected_env_var,
    )


def _collect_code_supplement_snapshots(
    *,
    codes: tuple[str, ...],
    api_key: str,
    selected_env_var: str,
    output_dir: Path,
    output_path: Path | None,
    timeout_seconds: int,
    get_json: JsonGet | None,
) -> KrxListedInfoSnapshotResult:
    output_path = output_path or _default_snapshot_output_path(output_dir)
    requester = get_json or _get_json
    total_count = 0
    saw_total_count = False
    records: list[dict[str, Any]] = []

    for code in codes:
        raw_json = fetch_krx_listed_info_page(
            api_key=api_key,
            page_no=1,
            page_count=DEFAULT_KRX_LISTED_INFO_CODE_PAGE_COUNT,
            timeout_seconds=timeout_seconds,
            get_json=requester,
            like_srtn_cd=code,
        )
        body = _response_body(raw_json)
        response_total_count = _safe_int(body.get("totalCount"), default=None)
        if response_total_count is not None:
            total_count += response_total_count
            saw_total_count = True
        record = build_krx_listed_info_raw_snapshot_record(
            code=code,
            request_date=utc_now_iso()[:10],
            raw_json=_with_request_context(
                raw_json,
                query_mode="code_supplement_latest",
                like_srtn_cd=code,
                page_no=1,
                page_count=DEFAULT_KRX_LISTED_INFO_CODE_PAGE_COUNT,
            ),
        )
        records.append(record)

    if records:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            for record in records:
                _write_record(handle, record)

    return KrxListedInfoSnapshotResult(
        output_path=output_path,
        records_written=len(records),
        total_count=total_count if saw_total_count else None,
        pages_collected=len(records),
        selected_env_var=selected_env_var,
        codes_requested=len(codes),
        query_mode="code_supplement_latest",
    )


def fetch_krx_listed_info_page(
    *,
    api_key: str,
    page_no: int,
    page_count: int,
    timeout_seconds: int,
    get_json: JsonGet | None = None,
    like_srtn_cd: str | None = None,
) -> dict[str, Any]:
    requester = get_json or _get_json
    params = {
        "serviceKey": api_key,
        "resultType": "json",
        "numOfRows": str(page_count),
        "pageNo": str(page_no),
    }
    if like_srtn_cd:
        params["likeSrtnCd"] = like_srtn_cd
    return requester(
        KRX_LISTED_INFO_URL,
        params,
        timeout_seconds,
    )


def build_krx_listed_info_raw_snapshot_record(
    *,
    request_date: str,
    raw_json: Any,
    code: str = "ALL",
    collected_at: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "provider": KRX_LISTED_INFO_PROVIDER,
        "endpoint_name": KRX_LISTED_INFO_ENDPOINT_NAME,
        "code": code,
        "collected_at": collected_at or utc_now_iso(),
        "request_date": request_date,
        "raw_json": raw_json,
        "raw_hash": compute_raw_hash(raw_json),
        "source_ref": KRX_LISTED_INFO_SOURCE_REF,
    }
    validate_krx_listed_info_raw_snapshot_record(record)
    return record


def validate_krx_listed_info_raw_snapshot_record(record: Mapping[str, Any]) -> None:
    missing = [field for field in RAW_SNAPSHOT_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"missing raw snapshot fields: {missing}")
    if record["provider"] != KRX_LISTED_INFO_PROVIDER:
        raise ValueError("provider must be data_go_kr_krx")
    if record["endpoint_name"] != KRX_LISTED_INFO_ENDPOINT_NAME:
        raise ValueError("endpoint_name must be krx_listed_info")
    if record["raw_hash"] != compute_raw_hash(record["raw_json"]):
        raise ValueError("raw_hash does not match raw_json")


def _get_json(url: str, params: Mapping[str, str], timeout_seconds: int) -> dict[str, Any]:
    request = Request(
        f"{url}?{urlencode(params, safe='%')}",
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - public data API URL.
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"KRX listed-info HTTP {exc.code}: {message}") from exc


def _select_api_key_env_var(env: Mapping[str, str]) -> str | None:
    for name in KRX_LISTED_INFO_API_KEY_ENV_VARS:
        if env.get(name, "").strip():
            return name
    return None


def _normalize_codes(codes: Iterable[str] | None) -> tuple[str, ...]:
    if codes is None:
        return ()
    seen: set[str] = set()
    normalized: list[str] = []
    for value in codes:
        code = str(value).strip()
        if not code:
            continue
        if code.startswith("A") and len(code) == 7:
            code = code[1:]
        code = code.zfill(6)
        if code in seen:
            continue
        seen.add(code)
        normalized.append(code)
    return tuple(normalized)


def _response_body(raw_json: Mapping[str, Any]) -> Mapping[str, Any]:
    response = raw_json.get("response", {})
    if not isinstance(response, Mapping):
        return {}
    body = response.get("body", {})
    return body if isinstance(body, Mapping) else {}


def _with_request_context(raw_json: dict[str, Any], **context: Any) -> dict[str, Any]:
    result = dict(raw_json)
    result["_request_context"] = context
    return result


def _write_record(handle: Any, record: Mapping[str, Any]) -> None:
    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
    handle.write("\n")


def _default_snapshot_output_path(output_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")
    return output_dir / timestamp[:8] / f"krx_listed_info_raw_snapshots_{timestamp}.jsonl"


def _safe_int(value: Any, *, default: int | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
