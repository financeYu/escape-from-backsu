"""OpenDART raw snapshot helpers for v1.4 PIT data supplements.

OpenDART can supplement disclosure receipt lineage and filing-based financial
raw data. It cannot supply analyst consensus estimate history or analyst
revision counts, so the snapshots created here remain candidate-only evidence
inputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import zipfile
from io import BytesIO
from typing import Any, Callable, Mapping, MutableMapping
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from stock_core.ml.kis_revision_snapshot_schema import (
    RAW_SNAPSHOT_REQUIRED_FIELDS,
    compute_raw_hash,
    utc_now_iso,
)
from stock_core.utils.local_env import check_local_env_presence, load_local_env_for_project
from stock_core.utils.paths import DATA_DIR, PROJECT_ROOT


OPENDART_PROVIDER = "opendart"
OPENDART_API_KEY_ENV_VAR = "OPENDART_API_KEY"
OPENDART_BASE_URL = "https://opendart.fss.or.kr"
DEFAULT_OPENDART_SNAPSHOT_DIR = DATA_DIR / "opendart_v1_4_raw_snapshots"

OPENDART_V1_4_ENDPOINTS: dict[str, dict[str, Any]] = {
    "corp_code": {
        "api_path": "/api/corpCode.xml",
        "request_fields": ("crtfc_key",),
        "response_fields": ("corp_code", "corp_name", "corp_eng_name", "stock_code", "modify_date"),
        "source_ref": "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018",
        "coverage": "stock_code_to_corp_code_lineage",
    },
    "disclosure_list": {
        "api_path": "/api/list.json",
        "request_fields": (
            "crtfc_key",
            "corp_code",
            "bgn_de",
            "end_de",
            "last_reprt_at",
            "pblntf_ty",
            "pblntf_detail_ty",
            "sort",
            "sort_mth",
            "page_no",
            "page_count",
        ),
        "response_fields": (
            "corp_cls",
            "corp_name",
            "corp_code",
            "stock_code",
            "report_nm",
            "rcept_no",
            "flr_nm",
            "rcept_dt",
            "rm",
        ),
        "source_ref": "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001",
        "coverage": "filing_receipt_date_and_report_number",
    },
    "single_account": {
        "api_path": "/api/fnlttSinglAcnt.json",
        "request_fields": ("crtfc_key", "corp_code", "bsns_year", "reprt_code"),
        "response_fields": (
            "rcept_no",
            "bsns_year",
            "stock_code",
            "reprt_code",
            "account_nm",
            "fs_div",
            "fs_nm",
            "sj_div",
            "sj_nm",
            "thstrm_nm",
            "thstrm_dt",
            "thstrm_amount",
            "thstrm_add_amount",
            "frmtrm_nm",
            "frmtrm_dt",
            "frmtrm_amount",
            "frmtrm_add_amount",
            "bfefrmtrm_nm",
            "bfefrmtrm_dt",
            "bfefrmtrm_amount",
            "ord",
            "currency",
        ),
        "source_ref": "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016",
        "coverage": "filing_based_financial_statement_accounts",
    },
    "alot_matter": {
        "api_path": "/api/alotMatter.json",
        "request_fields": ("crtfc_key", "corp_code", "bsns_year", "reprt_code"),
        "response_fields": (
            "rcept_no",
            "corp_cls",
            "corp_code",
            "corp_name",
            "se",
            "stock_knd",
            "thstrm",
            "frmtrm",
            "lwfr",
            "stlm_dt",
        ),
        "source_ref": "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS002&apiId=2019005",
        "coverage": "filing_based_dividend_matters",
    },
}

JsonGet = Callable[[str, Mapping[str, str], int], dict[str, Any]]
BytesGet = Callable[[str, Mapping[str, str], int], bytes]


@dataclass(frozen=True)
class OpenDartApiKeyConfig:
    api_key_present: bool
    checked_env_vars: tuple[str, ...] = (OPENDART_API_KEY_ENV_VAR,)
    source_paths: tuple[Path, ...] = ()
    attempted_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class OpenDartApiKeyReadiness:
    status: str
    missing_materials: tuple[str, ...]
    config_summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["missing_materials"] = list(self.missing_materials)
        return data


@dataclass(frozen=True)
class OpenDartSnapshotCollectionResult:
    output_path: Path
    records_written: int
    endpoint_counts: dict[str, int]
    missing_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "records_written": self.records_written,
            "endpoint_counts": dict(self.endpoint_counts),
            "missing_codes": list(self.missing_codes),
            "secret_values_redacted": True,
        }


def load_opendart_api_key_config(
    env: MutableMapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> OpenDartApiKeyConfig:
    source = os.environ if env is None else env
    presence = check_local_env_presence(
        (OPENDART_API_KEY_ENV_VAR,),
        project_root=project_root,
        environ=source,
    )
    return OpenDartApiKeyConfig(
        api_key_present=bool(source.get(OPENDART_API_KEY_ENV_VAR, "").strip()),
        source_paths=presence.source_paths,
        attempted_paths=presence.attempted_paths,
    )


def check_opendart_api_key_readiness(config: OpenDartApiKeyConfig) -> OpenDartApiKeyReadiness:
    missing = () if config.api_key_present else (OPENDART_API_KEY_ENV_VAR,)
    return OpenDartApiKeyReadiness(
        status="ready" if not missing else "blocked",
        missing_materials=missing,
        config_summary={
            "api_key_present": config.api_key_present,
            "checked_env_vars": list(config.checked_env_vars),
            "source_paths": [str(path) for path in config.source_paths],
            "attempted_paths": [str(path) for path in config.attempted_paths],
            "secret_values_redacted": True,
        },
    )


def collect_opendart_v1_4_raw_snapshots(
    *,
    codes: list[str] | tuple[str, ...],
    endpoints: list[str] | tuple[str, ...] | None = None,
    bgn_de: str,
    end_de: str,
    bsns_year: str,
    reprt_code: str,
    output_dir: Path = DEFAULT_OPENDART_SNAPSHOT_DIR,
    output_path: Path | None = None,
    env: MutableMapping[str, str] | None = None,
    project_root: Path = PROJECT_ROOT,
    timeout_seconds: int = 20,
    max_pages: int = 1,
    get_json: JsonGet | None = None,
    get_bytes: BytesGet | None = None,
) -> OpenDartSnapshotCollectionResult:
    selected_endpoints = tuple(endpoints or OPENDART_V1_4_ENDPOINTS.keys())
    _validate_collect_inputs(codes, selected_endpoints, bgn_de, end_de, bsns_year, reprt_code, max_pages)
    source = os.environ if env is None else env
    load_local_env_for_project(project_root, source)
    api_key = source.get(OPENDART_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise RuntimeError(f"OpenDART API key is not ready: missing {OPENDART_API_KEY_ENV_VAR}")

    output_path = output_path or _default_snapshot_output_path(output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    endpoint_counts = {endpoint_name: 0 for endpoint_name in selected_endpoints}
    records_written = 0
    missing_codes: list[str] = []
    requester_json = get_json or _get_json
    requester_bytes = get_bytes or _get_bytes
    corp_code_payload: dict[str, Any] | None = None
    corp_by_stock_code: dict[str, dict[str, str]] = {}

    if _needs_corp_codes(selected_endpoints):
        corp_code_payload = fetch_opendart_corp_code_payload(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            get_bytes=requester_bytes,
        )
        corp_by_stock_code = {
            str(row.get("stock_code", "")).strip(): row
            for row in corp_code_payload.get("list", [])
            if str(row.get("stock_code", "")).strip()
        }

    with output_path.open("a", encoding="utf-8") as handle:
        if "corp_code" in selected_endpoints and corp_code_payload is not None:
            record = build_opendart_raw_snapshot_record(
                endpoint_name="corp_code",
                code="ALL",
                request_date=utc_now_iso()[:10],
                raw_json=corp_code_payload,
            )
            _write_record(handle, record)
            records_written += 1
            endpoint_counts["corp_code"] += 1

        for raw_code in codes:
            code = _clean_code(raw_code)
            corp_row = corp_by_stock_code.get(code)
            if corp_row is None:
                missing_codes.append(code)
                continue
            corp_code = str(corp_row["corp_code"])

            if "disclosure_list" in selected_endpoints:
                for page_no in range(1, max_pages + 1):
                    raw_json = fetch_opendart_disclosure_list(
                        api_key=api_key,
                        corp_code=corp_code,
                        bgn_de=bgn_de,
                        end_de=end_de,
                        page_no=page_no,
                        timeout_seconds=timeout_seconds,
                        get_json=requester_json,
                    )
                    record = build_opendart_raw_snapshot_record(
                        endpoint_name="disclosure_list",
                        code=code,
                        request_date=f"{bgn_de}:{end_de}",
                        raw_json=_with_request_context(raw_json, code=code, corp_code=corp_code, page_no=page_no),
                    )
                    _write_record(handle, record)
                    records_written += 1
                    endpoint_counts["disclosure_list"] += 1
                    if page_no >= _safe_int(raw_json.get("total_page"), default=1):
                        break

            if "single_account" in selected_endpoints:
                raw_json = fetch_opendart_single_account(
                    api_key=api_key,
                    corp_code=corp_code,
                    bsns_year=bsns_year,
                    reprt_code=reprt_code,
                    timeout_seconds=timeout_seconds,
                    get_json=requester_json,
                )
                record = build_opendart_raw_snapshot_record(
                    endpoint_name="single_account",
                    code=code,
                    request_date=f"{bsns_year}:{reprt_code}",
                    raw_json=_with_request_context(raw_json, code=code, corp_code=corp_code),
                )
                _write_record(handle, record)
                records_written += 1
                endpoint_counts["single_account"] += 1

            if "alot_matter" in selected_endpoints:
                raw_json = fetch_opendart_alot_matter(
                    api_key=api_key,
                    corp_code=corp_code,
                    bsns_year=bsns_year,
                    reprt_code=reprt_code,
                    timeout_seconds=timeout_seconds,
                    get_json=requester_json,
                )
                record = build_opendart_raw_snapshot_record(
                    endpoint_name="alot_matter",
                    code=code,
                    request_date=f"{bsns_year}:{reprt_code}",
                    raw_json=_with_request_context(raw_json, code=code, corp_code=corp_code),
                )
                _write_record(handle, record)
                records_written += 1
                endpoint_counts["alot_matter"] += 1

    return OpenDartSnapshotCollectionResult(
        output_path=output_path,
        records_written=records_written,
        endpoint_counts=endpoint_counts,
        missing_codes=tuple(missing_codes),
    )


def fetch_opendart_corp_code_payload(
    *,
    api_key: str,
    timeout_seconds: int,
    get_bytes: BytesGet | None = None,
) -> dict[str, Any]:
    requester = get_bytes or _get_bytes
    payload = requester(
        f"{OPENDART_BASE_URL}{OPENDART_V1_4_ENDPOINTS['corp_code']['api_path']}",
        {"crtfc_key": api_key},
        timeout_seconds,
    )
    return {
        "status": "000",
        "message": "parsed_from_zip_xml",
        "list": _parse_corp_code_zip(payload),
    }


def fetch_opendart_disclosure_list(
    *,
    api_key: str,
    corp_code: str,
    bgn_de: str,
    end_de: str,
    page_no: int,
    timeout_seconds: int,
    get_json: JsonGet | None = None,
) -> dict[str, Any]:
    requester = get_json or _get_json
    return requester(
        f"{OPENDART_BASE_URL}{OPENDART_V1_4_ENDPOINTS['disclosure_list']['api_path']}",
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "last_reprt_at": "N",
            "pblntf_ty": "A",
            "sort": "date",
            "sort_mth": "desc",
            "page_no": str(page_no),
            "page_count": "100",
        },
        timeout_seconds,
    )


def fetch_opendart_single_account(
    *,
    api_key: str,
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    timeout_seconds: int,
    get_json: JsonGet | None = None,
) -> dict[str, Any]:
    requester = get_json or _get_json
    return requester(
        f"{OPENDART_BASE_URL}{OPENDART_V1_4_ENDPOINTS['single_account']['api_path']}",
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
        },
        timeout_seconds,
    )


def fetch_opendart_alot_matter(
    *,
    api_key: str,
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    timeout_seconds: int,
    get_json: JsonGet | None = None,
) -> dict[str, Any]:
    requester = get_json or _get_json
    return requester(
        f"{OPENDART_BASE_URL}{OPENDART_V1_4_ENDPOINTS['alot_matter']['api_path']}",
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
        },
        timeout_seconds,
    )


def build_opendart_raw_snapshot_record(
    *,
    endpoint_name: str,
    code: str,
    request_date: str,
    raw_json: Any,
    collected_at: str | None = None,
    provider: str = OPENDART_PROVIDER,
) -> dict[str, Any]:
    if endpoint_name not in OPENDART_V1_4_ENDPOINTS:
        raise ValueError(f"unsupported OpenDART endpoint: {endpoint_name}")
    record: dict[str, Any] = {
        "provider": provider,
        "endpoint_name": endpoint_name,
        "code": code,
        "collected_at": collected_at or utc_now_iso(),
        "request_date": request_date,
        "raw_json": raw_json,
        "raw_hash": compute_raw_hash(raw_json),
        "source_ref": str(OPENDART_V1_4_ENDPOINTS[endpoint_name]["source_ref"]),
    }
    validate_opendart_raw_snapshot_record(record)
    return record


def validate_opendart_raw_snapshot_record(record: Mapping[str, Any]) -> None:
    missing = [field for field in RAW_SNAPSHOT_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"missing raw snapshot fields: {missing}")
    if record["provider"] != OPENDART_PROVIDER:
        raise ValueError("provider must be opendart")
    if record["endpoint_name"] not in OPENDART_V1_4_ENDPOINTS:
        raise ValueError(f"unsupported OpenDART endpoint: {record['endpoint_name']}")
    if record["raw_hash"] != compute_raw_hash(record["raw_json"]):
        raise ValueError("raw_hash does not match raw_json")


def _get_json(url: str, params: Mapping[str, str], timeout_seconds: int) -> dict[str, Any]:
    request = Request(f"{url}?{urlencode(params)}", method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - OpenDART API URL.
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenDART HTTP {exc.code}: {message}") from exc


def _get_bytes(url: str, params: Mapping[str, str], timeout_seconds: int) -> bytes:
    request = Request(f"{url}?{urlencode(params)}", method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - OpenDART API URL.
            return response.read()
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenDART HTTP {exc.code}: {message}") from exc


def _parse_corp_code_zip(payload: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if not xml_names:
            raise ValueError("OpenDART corpCode zip does not contain XML")
        xml_bytes = archive.read(xml_names[0])

    root = ET.fromstring(xml_bytes)
    rows: list[dict[str, str]] = []
    for item in root.findall(".//list"):
        row = {
            "corp_code": _xml_text(item, "corp_code"),
            "corp_name": _xml_text(item, "corp_name"),
            "corp_eng_name": _xml_text(item, "corp_eng_name"),
            "stock_code": _xml_text(item, "stock_code"),
            "modify_date": _xml_text(item, "modify_date"),
        }
        rows.append(row)
    return rows


def _xml_text(item: ET.Element, name: str) -> str:
    child = item.find(name)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _needs_corp_codes(endpoints: tuple[str, ...]) -> bool:
    return bool({"corp_code", "disclosure_list", "single_account"} & set(endpoints))


def _with_request_context(raw_json: dict[str, Any], **context: Any) -> dict[str, Any]:
    result = dict(raw_json)
    result["_request_context"] = context
    return result


def _write_record(handle: Any, record: Mapping[str, Any]) -> None:
    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
    handle.write("\n")


def _default_snapshot_output_path(output_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")
    return output_dir / timestamp[:8] / f"opendart_v1_4_raw_snapshots_{timestamp}.jsonl"


def _validate_collect_inputs(
    codes: list[str] | tuple[str, ...],
    endpoints: tuple[str, ...],
    bgn_de: str,
    end_de: str,
    bsns_year: str,
    reprt_code: str,
    max_pages: int,
) -> None:
    if not codes:
        raise ValueError("at least one code is required")
    for code in codes:
        _clean_code(code)
    unknown = [endpoint_name for endpoint_name in endpoints if endpoint_name not in OPENDART_V1_4_ENDPOINTS]
    if unknown:
        raise ValueError(f"unsupported OpenDART endpoints: {unknown}")
    if not bgn_de or not end_de:
        raise ValueError("bgn_de and end_de are required")
    if "single_account" in endpoints and (not bsns_year or not reprt_code):
        raise ValueError("bsns_year and reprt_code are required for single_account")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")


def _clean_code(code: str) -> str:
    cleaned = str(code).strip()
    if not cleaned:
        raise ValueError("code is required")
    return cleaned.zfill(6) if cleaned.isdigit() else cleaned


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
