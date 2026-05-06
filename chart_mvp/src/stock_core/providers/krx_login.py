"""Secret-safe KRX login readiness helpers."""

from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from stock_core.utils.local_env import check_local_env_presence, load_local_env_for_project
from stock_core.utils.paths import PROJECT_ROOT


DEFAULT_KRX_LOGIN_URL = "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp"
DEFAULT_KRX_OPEN_API_USAGE_URL = "https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp"
DEFAULT_KRX_API_KEY_ENV_VARS = (
    "KRX_OPEN_API_KEY",
    "KRX_API_KEY",
    "KRX_SERVICE_KEY",
    "KRX_ACCESS_TOKEN",
)
DEFAULT_KRX_LOGIN_ID_ENV_VARS = ("KRX_ID",)
DEFAULT_KRX_LOGIN_PASSWORD_ENV_VARS = ("KRX_PASSWORD", "KRX_PW")
DEFAULT_NAVER_LOGIN_ID_ENV_VARS = ("KRX_NAVER_ID", "NAVER_ID")
DEFAULT_NAVER_LOGIN_PASSWORD_ENV_VARS = ("KRX_NAVER_PASSWORD", "NAVER_PASSWORD")
SAFE_CHALLENGE_POLICIES = {"manual_stop", "manual"}
SUPPORTED_LOGIN_METHODS = {"krx", "naver"}
SUPPORTED_DRIVERS = {"playwright"}


@dataclass(frozen=True)
class KrxLoginConfig:
    """Local KRX login automation settings without storing secret values."""

    login_url: str = DEFAULT_KRX_LOGIN_URL
    open_api_usage_url: str = DEFAULT_KRX_OPEN_API_USAGE_URL
    login_method: str = "krx"
    id_present: bool = False
    password_present: bool = False
    checked_id_env_vars: tuple[str, ...] = DEFAULT_KRX_LOGIN_ID_ENV_VARS
    checked_password_env_vars: tuple[str, ...] = DEFAULT_KRX_LOGIN_PASSWORD_ENV_VARS
    automation_allowed: bool = False
    driver: str = "playwright"
    headless: bool = False
    timeout_seconds: int = 120
    session_state_path: Path = PROJECT_ROOT / "data" / "krx" / "session_state.json"
    browser_user_data_dir: Path = PROJECT_ROOT / "data" / "krx" / "browser_profile"
    captcha_policy: str = "manual_stop"
    two_factor_policy: str = "manual_stop"
    success_url_contains: str = "data.krx.co.kr"


@dataclass(frozen=True)
class KrxLoginReadiness:
    """Secret-safe readiness result for KRX login automation."""

    status: str
    missing_materials: tuple[str, ...]
    warnings: tuple[str, ...]
    config_summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["missing_materials"] = list(self.missing_materials)
        data["warnings"] = list(self.warnings)
        return data


@dataclass(frozen=True)
class KrxLoginSessionResult:
    """Secret-safe result for a browser login attempt."""

    status: str
    login_method: str
    session_state_path: Path
    final_url: str
    manual_action_required: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "login_method": self.login_method,
            "session_state_path": str(self.session_state_path),
            "final_url": self.final_url,
            "manual_action_required": self.manual_action_required,
            "message": self.message,
            "secret_values_redacted": True,
        }


@dataclass(frozen=True)
class KrxApiKeyConfig:
    """Secret-safe KRX Open API key settings."""

    api_key_present: bool = False
    selected_env_var: str | None = None
    checked_env_vars: tuple[str, ...] = DEFAULT_KRX_API_KEY_ENV_VARS
    open_api_usage_url: str = DEFAULT_KRX_OPEN_API_USAGE_URL
    source_paths: tuple[Path, ...] = ()
    attempted_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class KrxApiKeyReadiness:
    """Secret-safe readiness result for KRX Open API key use."""

    status: str
    missing_materials: tuple[str, ...]
    warnings: tuple[str, ...]
    config_summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["missing_materials"] = list(self.missing_materials)
        data["warnings"] = list(self.warnings)
        return data


def _env_bool(value: str | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(value: str | None, *, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _resolve_local_path(value: str | None, *, default: Path, project_root: Path = PROJECT_ROOT) -> Path:
    if value is None or value.strip() == "":
        return default
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _secret_present(value: str | None) -> bool:
    return bool(value and value.strip())


def _first_present_name(source: Mapping[str, str], names: tuple[str, ...]) -> str | None:
    return next((name for name in names if _secret_present(source.get(name))), None)


def _login_credential_env_vars(login_method: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if login_method == "naver":
        return DEFAULT_NAVER_LOGIN_ID_ENV_VARS, DEFAULT_NAVER_LOGIN_PASSWORD_ENV_VARS
    return DEFAULT_KRX_LOGIN_ID_ENV_VARS, DEFAULT_KRX_LOGIN_PASSWORD_ENV_VARS


def _env_source(env: Mapping[str, str] | None, *, project_root: Path) -> Mapping[str, str]:
    if env is not None:
        return env
    load_local_env_for_project(project_root)
    return os.environ


def load_krx_login_config(
    env: Mapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> KrxLoginConfig:
    """Load a KRX login config from environment variables without exposing secrets."""

    source = _env_source(env, project_root=project_root)
    session_default = project_root / "data" / "krx" / "session_state.json"
    profile_default = project_root / "data" / "krx" / "browser_profile"
    login_method = source.get("KRX_LOGIN_METHOD", "krx").strip().lower() or "krx"
    id_env_vars, password_env_vars = _login_credential_env_vars(login_method)
    return KrxLoginConfig(
        login_url=source.get("KRX_LOGIN_URL", DEFAULT_KRX_LOGIN_URL),
        open_api_usage_url=source.get("KRX_OPEN_API_USAGE_URL", DEFAULT_KRX_OPEN_API_USAGE_URL),
        login_method=login_method,
        id_present=_first_present_name(source, id_env_vars) is not None,
        password_present=_first_present_name(source, password_env_vars) is not None,
        checked_id_env_vars=id_env_vars,
        checked_password_env_vars=password_env_vars,
        automation_allowed=_env_bool(source.get("KRX_LOGIN_AUTOMATION_ALLOWED"), default=False),
        driver=source.get("KRX_LOGIN_DRIVER", "playwright").strip().lower() or "playwright",
        headless=_env_bool(source.get("KRX_LOGIN_HEADLESS"), default=False),
        timeout_seconds=_env_int(source.get("KRX_LOGIN_TIMEOUT_SECONDS"), default=120),
        session_state_path=_resolve_local_path(
            source.get("KRX_SESSION_STATE_PATH"),
            default=session_default,
            project_root=project_root,
        ),
        browser_user_data_dir=_resolve_local_path(
            source.get("KRX_BROWSER_USER_DATA_DIR"),
            default=profile_default,
            project_root=project_root,
        ),
        captcha_policy=source.get("KRX_CAPTCHA_POLICY", "manual_stop").strip().lower() or "manual_stop",
        two_factor_policy=source.get("KRX_TWO_FACTOR_POLICY", "manual_stop").strip().lower() or "manual_stop",
        success_url_contains=source.get("KRX_LOGIN_SUCCESS_URL_CONTAINS", "data.krx.co.kr").strip(),
    )


def load_krx_api_key_config(
    env: Mapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
    key_env_vars: tuple[str, ...] = DEFAULT_KRX_API_KEY_ENV_VARS,
) -> KrxApiKeyConfig:
    """Load KRX Open API key presence from local env sources without exposing values."""

    source = _env_source(env, project_root=project_root)
    presence = check_local_env_presence(key_env_vars, project_root, source)
    selected = next((name for name in key_env_vars if _secret_present(source.get(name))), None)
    return KrxApiKeyConfig(
        api_key_present=selected is not None,
        selected_env_var=selected,
        checked_env_vars=key_env_vars,
        open_api_usage_url=source.get("KRX_OPEN_API_USAGE_URL", DEFAULT_KRX_OPEN_API_USAGE_URL),
        source_paths=presence.source_paths,
        attempted_paths=presence.attempted_paths,
    )


def check_krx_login_readiness(
    config: KrxLoginConfig,
    *,
    module_available: Mapping[str, bool] | None = None,
) -> KrxLoginReadiness:
    """Return missing KRX login materials without printing credentials."""

    missing: list[str] = []
    warnings: list[str] = []
    module_status = dict(module_available or {})

    if not config.automation_allowed:
        missing.append("KRX_LOGIN_AUTOMATION_ALLOWED=true")
    if config.login_method not in SUPPORTED_LOGIN_METHODS:
        missing.append(f"supported login method ({', '.join(sorted(SUPPORTED_LOGIN_METHODS))})")
    if not config.id_present:
        missing.append(" or ".join(config.checked_id_env_vars))
    if not config.password_present:
        missing.append(" or ".join(config.checked_password_env_vars))
    if config.driver not in SUPPORTED_DRIVERS:
        missing.append(f"supported driver ({', '.join(sorted(SUPPORTED_DRIVERS))})")
    elif not module_status.get(config.driver, importlib.util.find_spec(config.driver) is not None):
        missing.append(f"{config.driver} python package")
    if config.captcha_policy not in SAFE_CHALLENGE_POLICIES:
        missing.append("KRX_CAPTCHA_POLICY=manual_stop")
    if config.two_factor_policy not in SAFE_CHALLENGE_POLICIES:
        missing.append("KRX_TWO_FACTOR_POLICY=manual_stop")
    if not config.login_url.startswith("https://"):
        warnings.append("KRX_LOGIN_URL is not https")
    if not config.success_url_contains:
        warnings.append("KRX_LOGIN_SUCCESS_URL_CONTAINS is empty")

    summary = {
        "login_url": config.login_url,
        "open_api_usage_url": config.open_api_usage_url,
        "login_method": config.login_method,
        "id_present": config.id_present,
        "password_present": config.password_present,
        "checked_id_env_vars": list(config.checked_id_env_vars),
        "checked_password_env_vars": list(config.checked_password_env_vars),
        "automation_allowed": config.automation_allowed,
        "driver": config.driver,
        "headless": config.headless,
        "timeout_seconds": config.timeout_seconds,
        "session_state_path": str(config.session_state_path),
        "browser_user_data_dir": str(config.browser_user_data_dir),
        "captcha_policy": config.captcha_policy,
        "two_factor_policy": config.two_factor_policy,
        "success_url_contains": config.success_url_contains,
        "secret_values_redacted": True,
    }
    return KrxLoginReadiness(
        status="ready" if not missing else "blocked",
        missing_materials=tuple(missing),
        warnings=tuple(warnings),
        config_summary=summary,
    )


def check_krx_api_key_readiness(config: KrxApiKeyConfig) -> KrxApiKeyReadiness:
    """Return missing KRX Open API materials without printing key values."""

    missing: list[str] = []
    warnings: list[str] = []
    if not config.api_key_present:
        missing.append(" or ".join(config.checked_env_vars))
    if not config.open_api_usage_url.startswith("https://"):
        warnings.append("KRX_OPEN_API_USAGE_URL is not https")

    summary = {
        "api_key_present": config.api_key_present,
        "selected_env_var": config.selected_env_var,
        "checked_env_vars": list(config.checked_env_vars),
        "open_api_usage_url": config.open_api_usage_url,
        "source_paths": [str(path) for path in config.source_paths],
        "attempted_paths": [str(path) for path in config.attempted_paths],
        "secret_values_redacted": True,
    }
    return KrxApiKeyReadiness(
        status="ready" if not missing else "blocked",
        missing_materials=tuple(missing),
        warnings=tuple(warnings),
        config_summary=summary,
    )


def run_krx_login_session(
    env: Mapping[str, str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> KrxLoginSessionResult:
    """Run a visible Playwright login session and persist storage state.

    Naver/KRX additional verification is not bypassed. If it appears, the user
    must complete it manually in the opened browser before the timeout.
    """

    config = load_krx_login_config(env=env, project_root=project_root)
    readiness = check_krx_login_readiness(config)
    if readiness.status != "ready":
        return KrxLoginSessionResult(
            status="blocked",
            login_method=config.login_method,
            session_state_path=config.session_state_path,
            final_url="",
            manual_action_required=False,
            message=json.dumps(readiness.to_dict(), ensure_ascii=False, sort_keys=True),
        )

    source = _env_source(env, project_root=project_root)
    id_env_vars, password_env_vars = _login_credential_env_vars(config.login_method)
    user_id = source.get(_first_present_name(source, id_env_vars) or "", "")
    user_password = source.get(_first_present_name(source, password_env_vars) or "", "")

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    config.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
    config.session_state_path.parent.mkdir(parents=True, exist_ok=True)
    timeout_ms = config.timeout_seconds * 1000
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(config.browser_user_data_dir),
            headless=config.headless,
            timeout=timeout_ms,
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(config.login_url, wait_until="domcontentloaded", timeout=timeout_ms)
            if config.login_method == "naver":
                _click_naver_login(page, timeout_ms=timeout_ms)
                _fill_naver_login(page, user_id=user_id, user_password=user_password, timeout_ms=timeout_ms)
            else:
                _fill_direct_krx_login(page, user_id=user_id, user_password=user_password, timeout_ms=timeout_ms)
            page.wait_for_url(
                lambda url: config.success_url_contains in url,
                timeout=timeout_ms,
            )
            context.storage_state(path=str(config.session_state_path))
            final_url = page.url
            return KrxLoginSessionResult(
                status="ready",
                login_method=config.login_method,
                session_state_path=config.session_state_path,
                final_url=final_url,
                manual_action_required=False,
                message="login session saved",
            )
        except PlaywrightTimeoutError:
            context.storage_state(path=str(config.session_state_path))
            return KrxLoginSessionResult(
                status="manual_required",
                login_method=config.login_method,
                session_state_path=config.session_state_path,
                final_url=page.url,
                manual_action_required=True,
                message="login did not reach success URL before timeout; complete any visible challenge manually",
            )
        finally:
            context.close()


def _click_naver_login(page: object, *, timeout_ms: int) -> None:
    for locator in (
        page.get_by_text("네이버", exact=False),
        page.locator("a[href*='naver']").first,
        page.locator("button:has-text('네이버')").first,
    ):
        try:
            locator.click(timeout=timeout_ms // 3)
            return
        except Exception:
            continue
    raise RuntimeError("Naver linked-login control was not found")


def _fill_naver_login(page: object, *, user_id: str, user_password: str, timeout_ms: int) -> None:
    page.locator("#id").fill(user_id, timeout=timeout_ms)
    page.locator("#pw").fill(user_password, timeout=timeout_ms)
    page.locator("#log\\.login, button[type='submit'], input[type='submit']").first.click(timeout=timeout_ms)


def _fill_direct_krx_login(page: object, *, user_id: str, user_password: str, timeout_ms: int) -> None:
    id_selectors = ("input[name='id']", "input[name='userId']", "input[type='text']")
    password_selectors = ("input[name='password']", "input[name='pwd']", "input[type='password']")
    submit_selectors = ("button[type='submit']", "input[type='submit']", "button:has-text('로그인')")
    _fill_first_selector(page, id_selectors, user_id, timeout_ms=timeout_ms)
    _fill_first_selector(page, password_selectors, user_password, timeout_ms=timeout_ms)
    _click_first_selector(page, submit_selectors, timeout_ms=timeout_ms)


def _fill_first_selector(page: object, selectors: tuple[str, ...], value: str, *, timeout_ms: int) -> None:
    for selector in selectors:
        try:
            page.locator(selector).first.fill(value, timeout=timeout_ms // 3)
            return
        except Exception:
            continue
    raise RuntimeError(f"login field not found: {selectors[0]}")


def _click_first_selector(page: object, selectors: tuple[str, ...], *, timeout_ms: int) -> None:
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=timeout_ms // 3)
            return
        except Exception:
            continue
    raise RuntimeError(f"login submit control not found: {selectors[0]}")
