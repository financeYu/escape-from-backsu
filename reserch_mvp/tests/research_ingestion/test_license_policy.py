from __future__ import annotations

from research_ingestion.license_policy import annotate_license_policy, assess_license_policy, normalize_license_token


def test_noncommercial_creative_commons_license_is_allowed_for_noncommercial_research():
    result = assess_license_policy("https://creativecommons.org/licenses/by-nc/4.0/")

    assert result["license_collection_allowed"] is True
    assert result["license_noncommercial_allowed"] is True
    assert result["license_use_basis"] == "configured_noncommercial_license_match"


def test_license_token_normalization_handles_creative_commons_variants():
    assert normalize_license_token("CC BY-NC-SA 4.0") == "ccbyncsa"
    assert normalize_license_token("https://creativecommons.org/licenses/by/4.0/legalcode") == "ccby"


def test_unknown_license_requires_manual_review():
    result = assess_license_policy("publisher-custom-commercial-license")

    assert result["license_collection_allowed"] is False
    assert result["license_manual_review_required"] is True


def test_preannotated_source_license_policy_is_preserved(sample_paper):
    paper = sample_paper(
        license=None,
        license_collection_allowed=True,
        license_noncommercial_allowed=True,
        license_use_basis="nber_public_metadata_metadata_only",
        license_policy_notes_ko="NBER metadata-only 수집입니다.",
    )

    annotated = annotate_license_policy(paper)

    assert annotated["license_collection_allowed"] is True
    assert annotated["license_use_basis"] == "nber_public_metadata_metadata_only"
    assert annotated["manual_review_required"] is False
