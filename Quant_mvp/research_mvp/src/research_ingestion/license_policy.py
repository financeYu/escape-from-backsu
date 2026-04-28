from __future__ import annotations

import re
from typing import Any


OPEN_LICENSE_TOKENS = {
    "cc0",
    "publicdomain",
    "publicdomainmark",
    "ccby",
    "ccbysa",
    "ccbynd",
}

NONCOMMERCIAL_LICENSE_TOKENS = {
    "ccbync",
    "ccbyncsa",
    "ccbyncnd",
}


def assess_license_policy(license_value: str | None, policy_config: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy_config or {}
    allow_without_license = bool(policy.get("allow_metadata_without_license", True))
    allow_noncommercial = bool(policy.get("allow_noncommercial_licenses", True))
    manual_review_unknown = bool(policy.get("manual_review_when_license_unknown", False))
    token = normalize_license_token(license_value)

    if not token:
        return {
            "license_collection_allowed": allow_without_license,
            "license_noncommercial_allowed": None,
            "license_use_basis": "metadata_without_explicit_license",
            "license_manual_review_required": manual_review_unknown,
            "license_policy_notes_ko": (
                "명시 license가 없어 metadata-only 후보로 유지합니다."
                if allow_without_license
                else "명시 license가 없어 수집 허용 여부를 수동 검토해야 합니다."
            ),
        }

    if token in OPEN_LICENSE_TOKENS or _matches_configured_token(token, policy.get("allowed_open_license_tokens", [])):
        return _allowed_result(
            noncommercial_allowed=True,
            basis="configured_open_license_match",
            notes="명시 license가 open reuse 계열로 감지되어 metadata/abstract 후보 수집을 허용합니다.",
        )

    if token in NONCOMMERCIAL_LICENSE_TOKENS or _matches_configured_token(token, policy.get("allowed_noncommercial_license_tokens", [])):
        if allow_noncommercial:
            return _allowed_result(
                noncommercial_allowed=True,
                basis="configured_noncommercial_license_match",
                notes="비상업적 이용을 허용하는 license로 감지되어 metadata/abstract 후보 수집을 허용합니다.",
            )

    return {
        "license_collection_allowed": False,
        "license_noncommercial_allowed": False,
        "license_use_basis": "license_not_in_allowed_policy",
        "license_manual_review_required": True,
        "license_policy_notes_ko": "현재 policy에서 허용된 open/noncommercial license로 확인되지 않아 수동 검토가 필요합니다.",
    }


def assess_pdf_fulltext_policy(license_value: str | None, policy_config: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy_config or {}
    if policy.get("fulltext_download_remains_disabled", True):
        return _pdf_blocked_result(
            "fulltext_download_disabled_by_policy",
            "policy에서 PDF/fulltext 다운로드가 비활성화되어 있습니다.",
        )
    if not normalize_license_token(license_value):
        return _pdf_blocked_result(
            "missing_explicit_fulltext_license",
            "PDF/fulltext 수집에는 명시 license가 필요합니다.",
        )
    assessment = assess_license_policy(
        license_value,
        {
            **policy,
            "allow_metadata_without_license": False,
        },
    )
    if not assessment["license_collection_allowed"] or assessment["license_manual_review_required"]:
        return {
            **assessment,
            "pdf_fulltext_download_allowed": False,
            "pdf_fulltext_use_basis": assessment["license_use_basis"],
            "pdf_fulltext_policy_notes_ko": assessment["license_policy_notes_ko"],
        }
    return {
        **assessment,
        "pdf_fulltext_download_allowed": True,
        "pdf_fulltext_use_basis": assessment["license_use_basis"],
        "pdf_fulltext_policy_notes_ko": "명시 license가 정책상 허용되어 로컬 PDF 수집 후보로 인정됩니다.",
    }


def annotate_license_policy(paper: dict[str, Any], policy_config: dict[str, Any] | None = None) -> dict[str, Any]:
    annotated = dict(paper)
    assessment = assess_license_policy(annotated.get("license"), policy_config)
    for key, value in assessment.items():
        annotated.setdefault(key, value)
    if annotated["license_manual_review_required"]:
        annotated["manual_review_required"] = True
        notes = list(annotated.get("conflict_notes", []))
        note = annotated["license_policy_notes_ko"]
        if note not in notes:
            notes.append(note)
        annotated["conflict_notes"] = notes
    return annotated


def normalize_license_token(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower().strip()
    if "creativecommons.org/licenses/" in lowered:
        lowered = re.sub(r"^https?://", "", lowered)
        lowered = lowered.split("creativecommons.org/licenses/", 1)[1]
        license_slug = next((part for part in lowered.split("/") if part and not re.fullmatch(r"\d+(?:\.\d+)*", part)), "")
        lowered = f"cc-{license_slug}"
    lowered = lowered.replace("licenses/", "")
    lowered = lowered.replace("legalcode", "")
    lowered = re.sub(r"\b\d+(?:\.\d+)*\b", "", lowered)
    lowered = re.sub(r"\b(?:deed|en|us|international)\b", "", lowered)
    return re.sub(r"[^a-z0-9]+", "", lowered)


def _allowed_result(*, noncommercial_allowed: bool, basis: str, notes: str) -> dict[str, Any]:
    return {
        "license_collection_allowed": True,
        "license_noncommercial_allowed": noncommercial_allowed,
        "license_use_basis": basis,
        "license_manual_review_required": False,
        "license_policy_notes_ko": notes,
    }


def _matches_configured_token(token: str, configured: list[Any]) -> bool:
    return token in {normalize_license_token(str(item)) for item in configured if str(item).strip()}


def _pdf_blocked_result(basis: str, notes: str) -> dict[str, Any]:
    return {
        "license_collection_allowed": False,
        "license_noncommercial_allowed": None,
        "license_use_basis": basis,
        "license_manual_review_required": True,
        "license_policy_notes_ko": notes,
        "pdf_fulltext_download_allowed": False,
        "pdf_fulltext_use_basis": basis,
        "pdf_fulltext_policy_notes_ko": notes,
    }
