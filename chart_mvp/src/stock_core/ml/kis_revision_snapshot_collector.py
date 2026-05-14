"""KIS raw snapshot collection helpers for v1.4 revision diagnostics.

This module fetches raw KIS response bodies and stores append-only JSONL
snapshots. It does not normalize values into feature tables and does not place
revision fields on any feature allowlist.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from stock_core.ml.kis_revision_snapshot_schema import (
    KIS_PROVIDER,
    KIS_REVISION_ENDPOINTS,
    build_raw_snapshot_record,
)
from stock_core.utils.local_env import load_local_env_for_project
from stock_core.utils.paths import DATA_DIR, PROJECT_ROOT


KIS_TOKEN_EXPIRES_ENV_VAR = "KIS_ACCESS_TOKEN_EXPIRES_AT"
KIS_ENV_DV_ENV_VAR = "KIS_ENV_DV"
KIS_BASE_URL_ENV_VAR = "KIS_BASE_URL"
KIS_TOKEN_REFRESH_GRACE_MINUTES = 30
KIS_REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"
KIS_VIRTUAL_BASE_URL = "https://openapivts.koreainvestment.com:29443"
DEFAULT_SNAPSHOT_DIR = DATA_DIR / "kis_revision_raw_snapshots"

JsonPost = Callable[[str, Mapping[str, str], Mapping[str, Any], int], dict[str, Any]]
JsonGet = Callable[[str, Mapping[str, str], Mapping[str, str], int], tuple[dict[str, Any], Mapping[str, str]]]


@dataclass(frozen=True)
class KisTokenState:
    status: str
    token: str
    expires_at: str | None
    refreshed: bool
    source_path: Path
    env_dv: str
    base_url: str
    missing_materials: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def redacted_summary(self) -> dict[str, object]:
        return {
            "status": self.status,
            "access_token_present": bool(self.token),
            "expires_at": self.expires_at,
            "refreshed": self.refreshed,
            "source_path": str(self.source_path),
            "env_dv": self.env_dv,
            "base_url": self.base_url,
            "missing_materials": list(self.missing_materials),
            "warnings": list(self.warnings),
            "secret_values_redacted": True,
        }


@dataclass(frozen=True)
class KisSnapshotCollectionResult:
    output_path: Path
    records_written: int
    endpoint_counts: dict[str, int]
    token_refreshed: bool
    token_expires_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "records_written": self.records_written,
            "endpoint_counts": dict(self.endpoint_counts),
            "token_refreshed": self.token_refreshed,
            "token_expires_at": self.token_expires_at,
            "secret_values_redacted": True,
        }


def ensure_kis_access_token(
    *,
    env: MutableMapping[str, str] | None = None,
    project_root: Path = PROJECT_ROOT,
    force_refresh: bool = False,
    refresh_allowed: bool = True,
    timeout_seconds: int = 20,
    post_json: JsonPost | None = None,
) -> KisTokenState:
    """Return a usable KIS access token, refreshing and persisting if needed."""

    source = os.environ if env is None else env
    load_local_env_for_project(project_root, source)
    env_file = _default_api_key_file(project_root)
    app_key = source.get("KIS_APP_KEY", "").strip()
    app_secret = source.get("KIS_APP_SECRET", "").strip()
    token = source.get("KIS_ACCESS_TOKEN", "").strip()
    expires_at = source.get(KIS_TOKEN_EXPIRES_ENV_VAR, "").strip() or None
    env_dv = source.get(KIS_ENV_DV_ENV_VAR, "real").strip().lower() or "real"
    base_url = _resolve_kis_base_url(source, env_dv)

    if not app_key or not app_secret:
        missing = tuple(name for name, value in (("KIS_APP_KEY", app_key), ("KIS_APP_SECRET", app_secret)) if not value)
        return KisTokenState(
            status="blocked",
            token="",
            expires_at=expires_at,
            refreshed=False,
            source_path=env_file,
            env_dv=env_dv,
            base_url=base_url,
            missing_materials=missing,
        )

    if token and not force_refresh and _token_valid_for_grace(expires_at):
        return KisTokenState(
            status="ready",
            token=token,
            expires_at=expires_at,
            refreshed=False,
            source_path=env_file,
            env_dv=env_dv,
            base_url=base_url,
        )

    if not refresh_allowed:
        missing = () if token else ("KIS_ACCESS_TOKEN",)
        return KisTokenState(
            status="blocked",
            token="",
            expires_at=expires_at,
            refreshed=False,
            source_path=env_file,
            env_dv=env_dv,
            base_url=base_url,
            missing_materials=missing,
            warnings=("token_refresh_required",),
        )

    requester = post_json or _post_json
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    response = requester(
        f"{base_url}/oauth2/tokenP",
        {"content-type": "application/json; charset=utf-8"},
        payload,
        timeout_seconds,
    )
    new_token = str(response.get("access_token", "")).strip()
    if not new_token:
        return KisTokenState(
            status="blocked",
            token="",
            expires_at=expires_at,
            refreshed=False,
            source_path=env_file,
            env_dv=env_dv,
            base_url=base_url,
            missing_materials=("KIS_ACCESS_TOKEN",),
            warnings=("token_response_missing_access_token",),
        )

    new_expires_at = _extract_token_expiry(response)
    source["KIS_ACCESS_TOKEN"] = new_token
    if new_expires_at:
        source[KIS_TOKEN_EXPIRES_ENV_VAR] = new_expires_at
    _upsert_env_file(
        env_file,
        {
            "KIS_ACCESS_TOKEN": new_token,
            KIS_TOKEN_EXPIRES_ENV_VAR: new_expires_at or "",
        },
    )

    return KisTokenState(
        status="ready",
        token=new_token,
        expires_at=new_expires_at,
        refreshed=True,
        source_path=env_file,
        env_dv=env_dv,
        base_url=base_url,
        warnings=() if new_expires_at else ("token_response_missing_expiry",),
    )


def collect_kis_revision_raw_snapshots(
    *,
    codes: list[str] | tuple[str, ...],
    endpoints: list[str] | tuple[str, ...] | None = None,
    start_date: str,
    end_date: str,
    output_dir: Path = DEFAULT_SNAPSHOT_DIR,
    output_path: Path | None = None,
    env: MutableMapping[str, str] | None = None,
    project_root: Path = PROJECT_ROOT,
    force_refresh_token: bool = False,
    timeout_seconds: int = 20,
    max_pages: int = 1,
    get_json: JsonGet | None = None,
    post_json: JsonPost | None = None,
) -> KisSnapshotCollectionResult:
    """Collect KIS raw response snapshots for the selected endpoints."""

    selected_endpoints = tuple(endpoints or KIS_REVISION_ENDPOINTS.keys())
    _validate_collect_inputs(codes, selected_endpoints, start_date, end_date, max_pages)
    token_state = ensure_kis_access_token(
        env=env,
        project_root=project_root,
        force_refresh=force_refresh_token,
        timeout_seconds=timeout_seconds,
        post_json=post_json,
    )
    if token_state.status != "ready":
        raise RuntimeError(f"KIS token is not ready: {token_state.redacted_summary()}")

    output_path = output_path or _default_snapshot_output_path(output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    requester = get_json or _get_json
    records_written = 0
    endpoint_counts = {endpoint_name: 0 for endpoint_name in selected_endpoints}

    with output_path.open("a", encoding="utf-8") as handle:
        for code in codes:
            cleaned_code = _clean_code(code)
            for endpoint_name in selected_endpoints:
                for raw_json in _fetch_endpoint_pages(
                    endpoint_name=endpoint_name,
                    code=cleaned_code,
                    start_date=start_date,
                    end_date=end_date,
                    token_state=token_state,
                    app_key=(env or os.environ)["KIS_APP_KEY"],
                    app_secret=(env or os.environ)["KIS_APP_SECRET"],
                    timeout_seconds=timeout_seconds,
                    max_pages=max_pages,
                    requester=requester,
                ):
                    endpoint_meta = KIS_REVISION_ENDPOINTS[endpoint_name]
                    record = build_raw_snapshot_record(
                        endpoint_name=endpoint_name,
                        code=cleaned_code,
                        request_date=_request_date_key(endpoint_name, start_date, end_date),
                        raw_json=raw_json,
                        source_ref=str(endpoint_meta["source_ref"]),
                    )
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                    handle.write("\n")
                    records_written += 1
                    endpoint_counts[endpoint_name] += 1

    return KisSnapshotCollectionResult(
        output_path=output_path,
        records_written=records_written,
        endpoint_counts=endpoint_counts,
        token_refreshed=token_state.refreshed,
        token_expires_at=token_state.expires_at,
    )


def build_kis_revision_request_params(
    endpoint_name: str,
    *,
    code: str,
    start_date: str,
    end_date: str,
) -> dict[str, str]:
    """Build endpoint-specific query params from verified KIS examples."""

    cleaned_code = _clean_code(code)
    if endpoint_name == "estimate_perform":
        return {"SHT_CD": cleaned_code}
    if endpoint_name == "invest_opinion":
        return {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "16633",
            "FID_INPUT_ISCD": cleaned_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
        }
    if endpoint_name == "invest_opbysec":
        return {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "16634",
            "FID_INPUT_ISCD": cleaned_code,
            "FID_DIV_CLS_CODE": "0",
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
        }
    raise ValueError(f"unsupported KIS revision endpoint: {endpoint_name}")


def _fetch_endpoint_pages(
    *,
    endpoint_name: str,
    code: str,
    start_date: str,
    end_date: str,
    token_state: KisTokenState,
    app_key: str,
    app_secret: str,
    timeout_seconds: int,
    max_pages: int,
    requester: JsonGet,
) -> list[dict[str, Any]]:
    endpoint_meta = KIS_REVISION_ENDPOINTS[endpoint_name]
    url = f"{token_state.base_url}{endpoint_meta['api_path']}"
    params = build_kis_revision_request_params(
        endpoint_name,
        code=code,
        start_date=start_date,
        end_date=end_date,
    )
    headers = {
        "authorization": f"Bearer {token_state.token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": str(endpoint_meta["tr_id"]),
        "custtype": "P",
    }
    pages: list[dict[str, Any]] = []
    tr_cont = ""

    for _page_number in range(max_pages):
        page_headers = dict(headers)
        if tr_cont:
            page_headers["tr_cont"] = tr_cont
        raw_json, response_headers = requester(url, page_headers, params, timeout_seconds)
        pages.append(raw_json)
        tr_cont = str(response_headers.get("tr_cont") or response_headers.get("TR_CONT") or "").strip()
        if tr_cont not in {"M", "F"}:
            break

    return pages


def _post_json(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    return _open_json(request, timeout_seconds)


def _get_json(
    url: str,
    headers: Mapping[str, str],
    params: Mapping[str, str],
    timeout_seconds: int,
) -> tuple[dict[str, Any], Mapping[str, str]]:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers=dict(headers),
        method="GET",
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - user-configured KIS API URL.
        body = json.loads(response.read().decode("utf-8"))
        return body, dict(response.headers.items())


def _open_json(request: Request, timeout_seconds: int) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - user-configured KIS API URL.
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"KIS HTTP {exc.code}: {message}") from exc


def _resolve_kis_base_url(env: Mapping[str, str], env_dv: str) -> str:
    explicit = env.get(KIS_BASE_URL_ENV_VAR, "").strip()
    if explicit:
        return explicit.rstrip("/")
    if env_dv in {"vps", "virtual", "mock", "paper"}:
        return KIS_VIRTUAL_BASE_URL
    return KIS_REAL_BASE_URL


def _extract_token_expiry(response: Mapping[str, Any]) -> str | None:
    explicit = str(response.get("access_token_token_expired", "")).strip()
    if explicit:
        return explicit
    expires_in = response.get("expires_in")
    if expires_in is None:
        return None
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return (datetime.now() + timedelta(seconds=seconds)).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _token_valid_for_grace(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    expires_dt = _parse_token_expiry(expires_at)
    if expires_dt is None:
        return False
    return expires_dt > datetime.now() + timedelta(minutes=KIS_TOKEN_REFRESH_GRACE_MINUTES)


def _parse_token_expiry(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    return None


def _default_snapshot_output_path(output_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")
    day_dir = output_dir / timestamp[:8]
    return day_dir / f"kis_revision_raw_snapshots_{timestamp}.jsonl"


def _request_date_key(endpoint_name: str, start_date: str, end_date: str) -> str:
    if endpoint_name == "estimate_perform":
        return end_date
    return f"{start_date}:{end_date}"


def _validate_collect_inputs(
    codes: list[str] | tuple[str, ...],
    endpoints: tuple[str, ...],
    start_date: str,
    end_date: str,
    max_pages: int,
) -> None:
    if not codes:
        raise ValueError("at least one code is required")
    for code in codes:
        _clean_code(code)
    unknown = [endpoint_name for endpoint_name in endpoints if endpoint_name not in KIS_REVISION_ENDPOINTS]
    if unknown:
        raise ValueError(f"unsupported KIS revision endpoint: {unknown}")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")


def _clean_code(code: str) -> str:
    cleaned = str(code).strip()
    if not cleaned:
        raise ValueError("code is required")
    return cleaned


def _default_api_key_file(project_root: Path) -> Path:
    return _project_collection_root(project_root.resolve()) / "api_management" / "api_keys.env"


def _project_collection_root(project_root: Path) -> Path:
    for candidate in (project_root, *project_root.parents):
        if candidate.name.lower() == "project":
            return candidate
    return project_root.parent


def _upsert_env_file(path: Path, updates: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    remaining = dict(updates)
    new_lines: list[str] = []

    for raw_line in lines:
        parsed_name = _parse_env_name(raw_line)
        if parsed_name in remaining:
            new_lines.append(f"{parsed_name}={_format_env_value(remaining.pop(parsed_name))}")
        else:
            new_lines.append(raw_line)

    for name, value in remaining.items():
        new_lines.append(f"{name}={_format_env_value(value)}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _parse_env_name(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line.removeprefix("export ").strip()
    if "=" not in line:
        return None
    name = line.split("=", 1)[0].strip()
    if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
        return None
    return name


def _format_env_value(value: str) -> str:
    if value == "":
        return ""
    if any(char.isspace() for char in value) or "#" in value:
        return json.dumps(value, ensure_ascii=False)
    return value
