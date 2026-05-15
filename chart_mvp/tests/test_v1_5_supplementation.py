from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.v1_5_supplementation import (  # noqa: E402
    AVAILABILITY_POLICY_ID,
    V15SupplementationConfig,
    _valuation_scoring_readiness_rows,
    build_v1_5_supplementation,
)


class V15SupplementationTests(unittest.TestCase):
    def test_attaches_dart_metadata_but_keeps_rows_pending_until_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            metadata = root / "dart_metadata.csv"
            scores = root / "scores.jsonl"
            output = root / "out"
            self._write_pending_handoff(pending, financial)
            self._write_financial_cache(financial)
            self._write_dart_metadata(metadata)
            self._write_scores(scores)

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    dart_metadata_path=metadata,
                    technical_ml_scores_path=scores,
                    output_dir=output,
                )
            )

            enriched = result["metadata_enriched_rows"][0]
            self.assertEqual(enriched["corp_code"], "00126380")
            self.assertEqual(enriched["rcept_dt"], "20260515")
            self.assertEqual(enriched["availability_date"], "2026-05-18")
            self.assertEqual(enriched["availability_policy_id"], AVAILABILITY_POLICY_ID)
            self.assertEqual(enriched["pit_validation_status"], "pending_data")
            self.assertEqual(enriched["coverage_status"], "pending_data")
            self.assertIn("value_reconciliation_pending_external_source", enriched["pending_reason"])
            self.assertFalse(result["metadata_manifest"]["usable_as_available_v1_5_fundamentals"])
            self.assertEqual(result["source_lineage_report"]["hashed_source_row_count"], 1)
            self.assertEqual(result["limited_completion_update"]["promoted_fields"], [])
            self.assertEqual(result["baseline_comparison_rows"][0]["technical_ml_baseline_status"], "available")
            self.assertEqual(
                result["shadow_comparison_rows"][0]["comparison_status"],
                "skipped_insufficient_pit_fundamentals",
            )

    def test_missing_metadata_and_baseline_are_reported_as_pending_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            output = root / "out"
            self._write_pending_handoff(pending, financial)
            self._write_financial_cache(financial)

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    output_dir=output,
                    technical_ml_scores_path=root / "missing_scores.jsonl",
                )
            )

            self.assertEqual(result["metadata_manifest"]["metadata_import_status"], "missing")
            self.assertEqual(result["missing_requirements"]["metadata_import_status"], "missing")
            self.assertEqual(
                result["baseline_comparison_rows"][0]["technical_ml_baseline_status"],
                "skipped_missing_candidate_overlap",
            )
            self.assertEqual(
                result["incremental_report_rows"][0]["comparison_status"],
                "skipped_insufficient_pit_fundamentals",
            )
            self.assertTrue(Path(result["outputs"]["missing_requirements"]).exists())
            self.assertTrue(Path(result["outputs"]["limited_completion_update"]).exists())

    def test_uses_local_opendart_raw_snapshot_when_import_csv_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            raw_snapshot = root / "opendart_snapshot.jsonl"
            output = root / "out"
            self._write_pending_handoff(pending, financial)
            self._write_financial_cache(financial)
            self._write_raw_snapshot(raw_snapshot)

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    dart_raw_snapshot_path=raw_snapshot,
                    output_dir=output,
                )
            )

            enriched = result["metadata_enriched_rows"][0]
            self.assertEqual(enriched["corp_code"], "00126380")
            self.assertEqual(enriched["rcept_no"], "20260310002820")
            self.assertEqual(enriched["availability_date"], "2026-03-11")
            self.assertEqual(enriched["source_system"], "OpenDART_raw_snapshot")
            self.assertEqual(result["metadata_manifest"]["metadata_source_kind"], "raw_snapshot")
            self.assertEqual(result["metadata_manifest"]["metadata_import_status"], "available")
            self.assertEqual(len(result["dart_fundamental_collection_rows"]), 3)
            fundamental = result["dart_fundamental_collection_rows"][0]
            self.assertEqual(fundamental["account_nm"], "매출액")
            self.assertEqual(fundamental["value_reconciliation_status"], "collected_not_reconciled_to_chart_ratios")
            self.assertEqual(result["dart_fundamental_collection_manifest"]["row_count"], 3)
            self.assertFalse(result["limited_completion_update"]["usable_as_available_v1_5_fundamentals"])

    def test_reconciles_formula_mappable_quality_ratio_from_opendart_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            raw_snapshot = root / "opendart_snapshot.jsonl"
            output = root / "out"
            self._write_pending_handoff(pending, financial, field_name="operating_margin", value="10.0")
            self._write_financial_cache(financial, metric="OP_MARGIN", value="10.0")
            self._write_raw_snapshot(raw_snapshot)

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    dart_raw_snapshot_path=raw_snapshot,
                    output_dir=output,
                )
            )

            reconciliation = result["value_reconciliation_rows"][0]
            self.assertEqual(reconciliation["field_name"], "operating_margin")
            self.assertEqual(reconciliation["value_reconciliation_status"], "formula_match")
            self.assertEqual(reconciliation["dart_formula_id"], "opendart_operating_margin_v1")
            self.assertTrue(Path(result["outputs"]["value_reconciliation"]).exists())
            self.assertEqual(
                result["value_reconciliation_manifest"]["formula_match_fields"],
                ["operating_margin"],
            )
            readiness = result["valuation_scoring_readiness_rows"][0]
            self.assertEqual(readiness["quality_profitability_readiness_status"], "diagnostic_ready")
            self.assertEqual(readiness["candidate_overall_readiness_status"], "partial_diagnostic_ready")
            self.assertEqual(
                readiness["diagnostic_ready_quality_profitability_fields"],
                "operating_margin",
            )

    def test_market_backed_valuation_variance_stays_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data_dir = root / "data"
            output = data_dir / "v1_5_valuation"
            liquidity_dir = data_dir / "v1_3_liquidity"
            liquidity_dir.mkdir(parents=True)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            raw_snapshot = root / "opendart_snapshot.jsonl"
            self._write_pending_handoff(pending, financial, field_name="price_to_earnings", value="5.0")
            self._write_financial_cache(financial, metric="PER", value="5.0")
            self._write_raw_snapshot(raw_snapshot)
            self._write_market_snapshot(liquidity_dir / "v1_3_approved_local_market_cap_snapshot_20260501.csv")
            self._write_daily_price(data_dir / "005930_daily_prices.csv")

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    dart_raw_snapshot_path=raw_snapshot,
                    output_dir=output,
                )
            )

            reconciliation = result["value_reconciliation_rows"][0]
            self.assertEqual(reconciliation["field_name"], "price_to_earnings")
            self.assertEqual(reconciliation["value_reconciliation_status"], "formula_variance")
            self.assertEqual(reconciliation["dart_value"], "20.000000")
            self.assertEqual(result["value_reconciliation_manifest"]["formula_variance_fields"], ["price_to_earnings"])
            review = result["valuation_formula_reconciliation_review_rows"][0]
            self.assertEqual(review["field_name"], "price_to_earnings")
            self.assertEqual(review["reconciliation_status"], "blocked_reference_only_formula_variance")
            self.assertIn("adjusted_price_policy_mismatch", review["suspected_mismatch_reason"])
            self.assertIn("market_cap_policy_mismatch", review["suspected_mismatch_reason"])
            self.assertIn("shares_outstanding_policy_mismatch", review["suspected_mismatch_reason"])
            component = result["valuation_formula_component_rows"][0]
            self.assertEqual(component["market_cap"], "2000.000000")
            self.assertEqual(component["net_income"], "100.000000")
            self.assertEqual(component["eps"], "1.000000")
            self.assertEqual(component["chart_cache_eps"], "1.000000")
            self.assertEqual(component["chart_implied_price"], "5.000000")
            self.assertEqual(component["price_to_chart_implied_ratio"], "4.000000")
            self.assertEqual(component["component_quality_status"], "diagnostic_unadjusted_price_review_required")
            self.assertTrue(Path(result["outputs"]["valuation_formula_reconciliation_review"]).exists())
            self.assertTrue(Path(result["outputs"]["valuation_formula_components"]).exists())
            reconstruction = result["chart_ratio_policy_reconstruction_rows"][0]
            self.assertEqual(reconstruction["reconstruction_status"], "chart_ratio_internal_match_reference_only")
            self.assertEqual(reconstruction["chart_internal_recomputed_value"], "5.000000")
            self.assertEqual(reconstruction["evaluation_price_recomputed_value"], "20.000000")
            self.assertTrue(Path(result["outputs"]["chart_ratio_policy_reconstruction"]).exists())
            self.assertEqual(
                result["chart_ratio_policy_reconstruction_manifest"]["pit_promotion_status"],
                "blocked_requires_external_policy_lineage",
            )
            self.assertTrue(Path(result["outputs"]["valuation_formula_policy"]).exists())
            self.assertEqual(
                result["valuation_formula_reconciliation_review_manifest"]["reconciliation_status"],
                "blocked_reference_only_formula_variance",
            )
            self.assertEqual(
                result["valuation_formula_policy"]["chart_local_ratio_policy"],
                "reference_only_until_reconciled",
            )
            readiness = result["valuation_scoring_readiness_rows"][0]
            self.assertEqual(readiness["valuation_score_status"], "blocked_by_data")
            self.assertEqual(readiness["candidate_only_shadow_score_status"], "blocked_by_reconciliation")
            self.assertEqual(readiness["scoring_activation_allowed"], "false")
            self.assertIn("price_to_earnings", readiness["formula_variance_valuation_fields"])
            self.assertTrue(Path(result["outputs"]["valuation_scoring_readiness"]).exists())
            self.assertEqual(
                result["valuation_scoring_readiness_manifest"]["shadow_status_counts"],
                {"blocked_by_reconciliation": 1},
            )
            lineage = result["chart_local_ratio_source_lineage_rows"][0]
            self.assertEqual(lineage["chart_local_ratio_usage"], "reference_only_until_reconciled")
            self.assertEqual(lineage["lineage_status"], "source_row_hashed_policy_missing")
            self.assertIn("price_date_missing_for_chart_local_ratio", lineage["missing_lineage_reason"])
            policy_pack = result["chart_local_vendor_source_policy_pack_rows"][0]
            self.assertEqual(policy_pack["vendor_name"], "Naver Finance")
            self.assertEqual(policy_pack["policy_pack_status"], "incomplete_reference_only")
            self.assertIn("vendor_snapshot_date", policy_pack["missing_policy_fields"])
            self.assertEqual(policy_pack["scoring_activation_allowed"], "false")
            grid = result["per_pbr_formula_candidate_grid_rows"]
            self.assertEqual({row["formula_id"] for row in grid}, {
                "pe_market_cap_to_net_income",
                "pe_close_x_shares_to_net_income",
                "pe_adjusted_close_x_shares_to_net_income",
                "pe_close_to_eps",
                "pe_adjusted_close_to_eps",
            })
            self.assertEqual(
                result["per_pbr_formula_match_report"]["overall_recommendation"],
                "no_safe_match_keep_blocked",
            )
            feature = result["feature_level_readiness_rows"][0]
            self.assertEqual(feature["field_name"], "price_to_earnings")
            self.assertEqual(feature["feature_readiness_status"], "blocked_by_reconciliation")
            self.assertEqual(feature["scoring_activation_allowed"], "false")
            self.assertFalse(result["limited_completion_update"]["usable_as_available_v1_5_fundamentals"])

    def test_naver_ratio_policy_snapshot_enriches_policy_pack_without_promoting_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            naver_snapshot = root / "naver_policy.csv"
            output = root / "out"
            self._write_pending_handoff(pending, financial)
            self._write_financial_cache(financial)
            self._write_naver_ratio_policy_snapshot(naver_snapshot)

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    naver_ratio_policy_snapshot_path=naver_snapshot,
                    output_dir=output,
                )
            )

            lineage = result["chart_local_ratio_source_lineage_rows"][0]
            self.assertEqual(lineage["vendor_snapshot_date"], "2026-05-15T11:00:00+00:00")
            self.assertEqual(lineage["price_date"], "2026-05-15")
            self.assertEqual(lineage["unadjusted_price_policy"], "naver_main_current_price")
            self.assertEqual(lineage["source_available_before_evaluation_date"], "verified")
            self.assertEqual(
                lineage["lineage_status"],
                "source_row_hashed_naver_policy_snapshot_attached_pit_unproven",
            )
            self.assertIn("adjusted_price_policy_missing", lineage["missing_lineage_reason"])
            policy_pack = result["chart_local_vendor_source_policy_pack_rows"][0]
            self.assertEqual(policy_pack["policy_pack_status"], "partially_enriched_reference_only")
            self.assertEqual(policy_pack["source_available_date"], "2026-05-15")
            self.assertEqual(policy_pack["price_policy"], "naver_main_current_price")
            self.assertIn("adjusted_price_policy", policy_pack["missing_policy_fields"])
            feature = result["feature_level_readiness_rows"][0]
            self.assertEqual(feature["feature_readiness_status"], "blocked_by_reconciliation")
            self.assertEqual(feature["scoring_activation_allowed"], "false")
            self.assertEqual(result["naver_ratio_policy_snapshot_rows"][0]["ticker"], "005930")

    def test_naver_asof_resolver_keeps_past_dates_reference_only_and_future_dates_vendor_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_html = root / "raw.html"
            raw_html.write_text("<html>fixture</html>", encoding="utf-8")
            raw_hash = hashlib.sha256(raw_html.read_bytes()).hexdigest()

            past_pending = root / "past_pending.csv"
            future_pending = root / "future_pending.csv"
            financial = root / "005930_financial_statements.csv"
            naver_snapshot = root / "naver_policy.csv"
            self._write_pending_handoff(past_pending, financial, evaluation_date="2026-05-14")
            self._write_pending_handoff(future_pending, financial, evaluation_date="2026-05-20")
            self._write_financial_cache(financial)
            self._write_naver_ratio_policy_snapshot(
                naver_snapshot,
                raw_html_path=str(raw_html),
                raw_html_sha256=raw_hash,
                source_available_date="2026-05-15",
            )

            past = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=past_pending,
                    naver_ratio_policy_snapshot_path=naver_snapshot,
                    output_dir=root / "past_out",
                )
            )
            future = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=future_pending,
                    naver_ratio_policy_snapshot_path=naver_snapshot,
                    output_dir=root / "future_out",
                )
            )

            self.assertEqual(
                past["naver_ratio_asof_resolved_rows"][0]["asof_resolution_status"],
                "after_evaluation_date",
            )
            past_split = past["per_pbr_split_readiness_rows"][0]
            self.assertEqual(past_split["diagnostic_usage_status"], "reference_only_after_evaluation_date")
            self.assertEqual(past_split["formula_reconciled_status"], "blocked_by_reconciliation")
            self.assertEqual(past_split["formula_verified"], "false")

            self.assertEqual(
                future["naver_ratio_asof_resolved_rows"][0]["asof_resolution_status"],
                "vendor_snapshot_available_asof_evaluation",
            )
            future_split = future["per_pbr_split_readiness_rows"][0]
            self.assertEqual(future_split["diagnostic_usage_status"], "vendor_reference_ready")
            self.assertEqual(future_split["adjusted_price_policy"], "not_disclosed_by_naver_main")
            self.assertEqual(future_split["scoring_activation_allowed"], "false")
            handoff = future["v1_6_readiness_handoff_rows"][0]
            self.assertEqual(handoff["overall_valuation_status"], "vendor_reference_only")
            self.assertEqual(handoff["manual_review_required"], "true")
            self.assertIn("v1_6_consumes_status_flags_only", handoff["limitations"])
            self.assertNotIn("valuation_score", handoff)
            self.assertEqual(
                handoff["price_to_earnings_canonical_formula_status"],
                "blocked_by_reconciliation",
            )
            self.assertEqual(
                handoff["price_to_earnings_vendor_reference_status"],
                "vendor_reference_only",
            )
            self.assertEqual(
                handoff["incremental_evidence_status"],
                "skipped_missing_baseline_artifacts",
            )
            self.assertTrue(Path(future["outputs"]["v1_6_readiness_handoff"]).exists())

    def test_naver_vendor_snapshot_readiness_requires_raw_html_hash_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_html = root / "raw.html"
            raw_html.write_text("<html>fixture</html>", encoding="utf-8")
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            naver_snapshot = root / "naver_policy.csv"
            self._write_pending_handoff(pending, financial, evaluation_date="2026-05-20")
            self._write_financial_cache(financial)
            self._write_naver_ratio_policy_snapshot(
                naver_snapshot,
                raw_html_path=str(raw_html),
                raw_html_sha256="wrong_hash",
                source_available_date="2026-05-15",
            )

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    naver_ratio_policy_snapshot_path=naver_snapshot,
                    output_dir=root / "out",
                )
            )

            self.assertEqual(result["naver_ratio_asof_snapshot_registry_rows"][0]["crawl_status"], "hash_mismatch")
            self.assertEqual(result["naver_ratio_asof_resolved_rows"][0]["asof_resolution_status"], "hash_mismatch")
            split = result["per_pbr_split_readiness_rows"][0]
            self.assertEqual(split["diagnostic_usage_status"], "reference_only_hash_mismatch")
            self.assertEqual(result["naver_daily_crawl_health"]["hash_mismatch_count"], 1)

    def test_naver_vendor_snapshot_readiness_requires_raw_html_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_html = root / "raw.html"
            raw_html.write_text("<html>fixture</html>", encoding="utf-8")
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            naver_snapshot = root / "naver_policy.csv"
            self._write_pending_handoff(pending, financial, evaluation_date="2026-05-20")
            self._write_financial_cache(financial)
            self._write_naver_ratio_policy_snapshot(
                naver_snapshot,
                raw_html_path=str(raw_html),
                raw_html_sha256="",
                source_available_date="2026-05-15",
            )

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    naver_ratio_policy_snapshot_path=naver_snapshot,
                    output_dir=root / "out",
                )
            )

            self.assertEqual(
                result["naver_ratio_asof_snapshot_registry_rows"][0]["crawl_status"],
                "raw_html_sha256_missing",
            )
            self.assertEqual(
                result["naver_ratio_asof_resolved_rows"][0]["asof_resolution_status"],
                "raw_html_sha256_missing",
            )
            split = result["per_pbr_split_readiness_rows"][0]
            self.assertEqual(split["diagnostic_usage_status"], "reference_only_raw_html_sha256_missing")
            self.assertEqual(
                result["naver_daily_crawl_health"]["crawl_status_counts"]["raw_html_sha256_missing"],
                1,
            )

    def test_formula_match_still_requires_verified_chart_ratio_lineage_for_readiness(self) -> None:
        pending_rows = [
            {
                "candidate_id": "sc_v1_5_diag",
                "evidence_id": "ee_v1_5_diag",
                "ticker": "005930",
                "field_name": "price_to_earnings",
            },
            {
                "candidate_id": "sc_v1_5_diag",
                "evidence_id": "ee_v1_5_diag",
                "ticker": "005930",
                "field_name": "price_to_book",
            },
        ]
        reconciliation_rows = [
            {
                "candidate_id": "sc_v1_5_diag",
                "field_name": "price_to_earnings",
                "value_reconciliation_status": "formula_match",
            },
            {
                "candidate_id": "sc_v1_5_diag",
                "field_name": "price_to_book",
                "value_reconciliation_status": "formula_match",
            },
        ]
        ratio_lineage_rows = [
            {
                "candidate_id": "sc_v1_5_diag",
                "chart_local_per": "10.0",
                "lineage_status": "source_row_hashed_naver_policy_snapshot_attached_pit_unproven",
            },
            {
                "candidate_id": "sc_v1_5_diag",
                "chart_local_pbr": "1.0",
                "lineage_status": "source_row_hashed_naver_policy_snapshot_attached_pit_unproven",
            },
        ]

        rows = _valuation_scoring_readiness_rows(pending_rows, reconciliation_rows, ratio_lineage_rows)

        readiness = rows[0]
        self.assertEqual(readiness["valuation_readiness_status"], "blocked_by_reconciliation")
        self.assertEqual(readiness["candidate_only_shadow_score_status"], "blocked_by_reconciliation")
        self.assertEqual(readiness["eligible_field_count"], "0")
        self.assertEqual(
            readiness["missing_core_valuation_fields"],
            "price_to_book|price_to_earnings",
        )
        self.assertEqual(readiness["scoring_activation_allowed"], "false")

    def test_dividend_pit_source_lineage_can_be_diagnostic_ready_without_scoring_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data_dir = root / "data"
            output = data_dir / "v1_5_valuation"
            liquidity_dir = data_dir / "v1_3_liquidity"
            liquidity_dir.mkdir(parents=True)
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            raw_snapshot = root / "opendart_snapshot.jsonl"
            self._write_pending_handoff(pending, financial, field_name="dividend_yield", value="2.5")
            self._write_financial_cache(financial, metric="배당수익률", value="2.5")
            self._write_raw_snapshot(raw_snapshot, include_dividend=True)
            self._write_market_snapshot(liquidity_dir / "v1_3_approved_local_market_cap_snapshot_20260501.csv")
            self._write_daily_price(data_dir / "005930_daily_prices.csv")

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    dart_raw_snapshot_path=raw_snapshot,
                    output_dir=output,
                )
            )

            dividend = result["dividend_pit_source_lineage_rows"][0]
            self.assertEqual(dividend["dividend_per_share"], "1000")
            self.assertEqual(dividend["availability_date"], "2026-03-11")
            self.assertEqual(dividend["pit_dividend_source_status"], "diagnostic_ready")
            feature = result["feature_level_readiness_rows"][0]
            self.assertEqual(feature["field_name"], "dividend_yield")
            self.assertEqual(feature["feature_readiness_status"], "diagnostic_ready")
            self.assertEqual(feature["scoring_activation_allowed"], "false")
            readiness = result["valuation_scoring_readiness_rows"][0]
            self.assertEqual(readiness["dividend_readiness_status"], "diagnostic_ready")
            self.assertEqual(readiness["scoring_activation_allowed"], "false")

    def test_completion_remediation_artifacts_keep_limited_complete_and_skip_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data_dir = root / "data"
            output = data_dir / "v1_5_valuation"
            liquidity_dir = data_dir / "v1_3_liquidity"
            liquidity_dir.mkdir(parents=True)
            raw_html = root / "raw.html"
            raw_html.write_text("<html>fixture</html>", encoding="utf-8")
            raw_hash = hashlib.sha256(raw_html.read_bytes()).hexdigest()
            pending = root / "pending.csv"
            financial = root / "005930_financial_statements.csv"
            raw_snapshot = root / "opendart_snapshot.jsonl"
            naver_snapshot = root / "naver_policy.csv"
            self._write_multi_field_pending_handoff(pending, financial, evaluation_date="2026-05-20")
            self._write_financial_cache(financial, metric="PER", value="5.0")
            self._write_raw_snapshot(raw_snapshot)
            self._write_market_snapshot(liquidity_dir / "v1_3_approved_local_market_cap_snapshot_20260501.csv")
            self._write_daily_price(data_dir / "005930_daily_prices.csv")
            self._write_naver_ratio_policy_snapshot(
                naver_snapshot,
                raw_html_path=str(raw_html),
                raw_html_sha256=raw_hash,
                source_available_date="2026-05-15",
            )

            result = build_v1_5_supplementation(
                V15SupplementationConfig(
                    pending_handoff_path=pending,
                    dart_raw_snapshot_path=raw_snapshot,
                    naver_ratio_policy_snapshot_path=naver_snapshot,
                    technical_ml_scores_path=root / "missing_scores.jsonl",
                    output_dir=output,
                )
            )

            canonical = result["canonical_valuation_component_rows"]
            self.assertEqual({row["field_name"] for row in canonical}, {"price_to_book", "price_to_earnings"})
            self.assertIn(
                "missing_component",
                {row["component_status"] for row in canonical},
            )
            matrix = result["per_pbr_reconciliation_matrix_rows"]
            self.assertIn("vendor_reference_only", {row["reconciliation_status"] for row in matrix})
            self.assertIn("blocked_by_reconciliation", {row["reconciliation_status"] for row in matrix})
            real = result["incremental_real_comparison_rows"][0]
            self.assertEqual(real["comparison_status"], "skipped_missing_baseline_artifacts")
            self.assertEqual(real["horizon_id"], "missing_horizon_id")
            gap = result["complete_readiness_gap_report"]
            self.assertEqual(gap["current_verdict"], "LIMITED COMPLETE")
            self.assertEqual(gap["complete_readiness_status"], "not_ready_for_COMPLETE")
            self.assertIn("price_to_earnings", gap["per_pbr_reconciliation_status"])
            hygiene = result["completion_hygiene_report"]
            self.assertEqual(hygiene["final_verdict"], "LIMITED COMPLETE")
            self.assertFalse(hygiene["scoring_activation_allowed"])
            self.assertTrue(Path(result["outputs"]["completion_hygiene_report"]).exists())
            self.assertTrue(Path(result["outputs"]["complete_readiness_gap_report"]).exists())
            self.assertTrue(Path(result["outputs"]["canonical_valuation_component_table"]).exists())
            self.assertTrue(Path(result["outputs"]["per_pbr_reconciliation_matrix"]).exists())
            self.assertTrue(Path(result["outputs"]["incremental_valuation_real_comparison"]).exists())
            self.assertTrue(Path(result["outputs"]["dividend_yield_readiness"]).exists())
            debug = result["per_pbr_variance_debug_rows"][0]
            self.assertEqual(debug["recommended_formula_route"], "near_match_needs_review")
            self.assertIn("eps_bps_denominator_mismatch", debug["suspected_pe_mismatch_reason"])
            route = result["per_pbr_formula_route_decision"]
            self.assertEqual(route["decision"], "near_match_needs_review")
            self.assertFalse(route["formula_reconciled_ready"])
            baseline_check = result["incremental_baseline_dependency_check"]
            self.assertEqual(
                baseline_check["dependency_check_status"],
                "skipped_missing_baseline_artifacts",
            )
            self.assertIn(
                "technical_ml_baseline_row",
                baseline_check["missing_keys_by_candidate"]["sc_v1_5_diag"],
            )
            start_report = result["v1_6_start_readiness_report"]
            self.assertTrue(start_report["can_start_v1_6"])
            self.assertEqual(start_report["start_basis"], "readiness_status_flags_only")
            self.assertIn("valuation_score", start_report["fields_explicitly_not_used_as_score"])
            self.assertTrue(Path(result["outputs"]["v1_6_start_readiness_report"]).exists())
            self.assertTrue(Path(result["outputs"]["per_pbr_variance_debug"]).exists())
            self.assertTrue(Path(result["outputs"]["per_pbr_formula_route_decision"]).exists())
            self.assertTrue(Path(result["outputs"]["incremental_baseline_dependency_check"]).exists())

    @staticmethod
    def _write_multi_field_pending_handoff(
        path: Path,
        financial_path: Path,
        *,
        evaluation_date: str = "2026-05-20",
    ) -> None:
        fieldnames = [
            "candidate_id",
            "evidence_id",
            "ticker",
            "company_name",
            "evaluation_date",
            "fiscal_period",
            "report_period_end_date",
            "source_ref",
            "field_name",
            "value",
            "unit",
            "currency",
            "sector_id",
            "industry_id",
            "industry_name",
            "data_quality_flags",
            "pending_reason",
            "source_metric",
            "source_period",
            "source_financial_cache_path",
            "boundary_notice",
        ]
        rows = [
            ("price_to_earnings", "PER", "5.0", "multiple"),
            ("price_to_book", "PBR", "2.0", "multiple"),
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for field_name, source_metric, value, unit in rows:
                writer.writerow(
                    {
                        "candidate_id": "sc_v1_5_diag",
                        "evidence_id": "ee_v1_5_diag",
                        "ticker": "005930",
                        "company_name": "Samsung Electronics",
                        "evaluation_date": evaluation_date,
                        "fiscal_period": "FY2025",
                        "report_period_end_date": "2025-12-31",
                        "source_ref": "chart_cache",
                        "field_name": field_name,
                        "value": value,
                        "unit": unit,
                        "currency": "",
                        "sector_id": "krx_sector:technology",
                        "industry_id": "",
                        "industry_name": "Technology",
                        "data_quality_flags": "chart_mvp_financial_cache|not_pit_verified",
                        "pending_reason": "availability_date_missing;filing_or_disclosure_date_missing",
                        "source_metric": source_metric,
                        "source_period": "FY2025",
                        "source_financial_cache_path": str(financial_path),
                        "boundary_notice": "pending_data_only",
                    }
                )

    @staticmethod
    def _write_pending_handoff(
        path: Path,
        financial_path: Path,
        *,
        field_name: str = "price_to_earnings",
        value: str = "10.5",
        evaluation_date: str = "2026-05-20",
    ) -> None:
        fieldnames = [
            "candidate_id",
            "evidence_id",
            "ticker",
            "company_name",
            "evaluation_date",
            "fiscal_period",
            "report_period_end_date",
            "source_ref",
            "field_name",
            "value",
            "unit",
            "currency",
            "sector_id",
            "industry_id",
            "industry_name",
            "data_quality_flags",
            "pending_reason",
            "source_metric",
            "source_period",
            "source_financial_cache_path",
            "boundary_notice",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {
                    "candidate_id": "sc_v1_5_diag",
                    "evidence_id": "ee_v1_5_diag",
                    "ticker": "005930",
                    "company_name": "Samsung Electronics",
                    "evaluation_date": evaluation_date,
                    "fiscal_period": "FY2025",
                    "report_period_end_date": "2025-12-31",
                    "source_ref": "chart_cache",
                    "field_name": field_name,
                    "value": value,
                    "unit": "multiple",
                    "currency": "",
                    "sector_id": "krx_sector:technology",
                    "industry_id": "",
                    "industry_name": "Technology",
                    "data_quality_flags": "chart_mvp_financial_cache|not_pit_verified",
                    "pending_reason": "availability_date_missing;filing_or_disclosure_date_missing",
                    "source_metric": "PER",
                    "source_period": "FY2025",
                    "source_financial_cache_path": str(financial_path),
                    "boundary_notice": "pending_data_only",
                }
            )

    @staticmethod
    def _write_financial_cache(path: Path, *, metric: str = "PER", value: str = "10.5") -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["code", "metric", "period", "value"])
            writer.writeheader()
            writer.writerow({"code": "005930", "metric": metric, "period": "FY2025", "value": value})
            writer.writerow({"code": "005930", "metric": "EPS(원)", "period": "FY2025", "value": "1.0"})
            writer.writerow({"code": "005930", "metric": "BPS(원)", "period": "FY2025", "value": "2.0"})

    @staticmethod
    def _write_naver_ratio_policy_snapshot(
        path: Path,
        *,
        raw_html_path: str = "raw.html",
        raw_html_sha256: str = "fixture",
        source_available_date: str = "2026-05-15",
    ) -> None:
        fieldnames = [
            "schema_version",
            "ticker",
            "vendor_name",
            "vendor_or_origin",
            "source_system",
            "source_url",
            "vendor_snapshot_date",
            "vendor_as_of_date",
            "source_available_date",
            "source_available_policy",
            "price_basis_datetime",
            "price_date",
            "price_value",
            "price_policy",
            "adjusted_price_policy",
            "shares_outstanding",
            "shares_policy",
            "eps_policy",
            "bps_policy",
            "per_formula",
            "pbr_formula",
            "dividend_yield_formula",
            "per_reported_value",
            "eps_reported_value",
            "pbr_reported_value",
            "bps_reported_value",
            "raw_html_sha256",
            "raw_html_path",
            "source_lineage_status",
            "missing_policy_fields",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {
                    "schema_version": "v1_5_naver_ratio_policy_snapshot_v1_0",
                    "ticker": "005930",
                    "vendor_name": "Naver Finance",
                    "vendor_or_origin": "Naver Finance main.naver",
                    "source_system": "NaverFinance_main_page",
                    "source_url": "https://finance.naver.com/item/main.naver?code=005930",
                    "vendor_snapshot_date": "2026-05-15T11:00:00+00:00",
                    "vendor_as_of_date": "2026-05-15",
                    "source_available_date": source_available_date,
                    "source_available_policy": "crawl_fetch_date_only_not_historical_vendor_publication_date",
                    "price_basis_datetime": "2026-05-15T16:10:00[closed]",
                    "price_date": "2026-05-15",
                    "price_value": "270,500",
                    "price_policy": "naver_main_current_price",
                    "adjusted_price_policy": "not_disclosed_by_naver_main",
                    "shares_outstanding": "5,846,278,608",
                    "shares_policy": "eps_policy|bps_policy",
                    "eps_policy": "controlling_owner_recent_4q_net_income_divided_by_modified_average_issued_shares_common_plus_preferred",
                    "bps_policy": "recent_quarter_equity_divided_by_modified_period_end_floating_shares_common_plus_preferred",
                    "per_formula": "current_price_divided_by_eps_vendor_reported",
                    "pbr_formula": "current_price_divided_by_bps_vendor_reported",
                    "dividend_yield_formula": "dividend_per_share_divided_by_current_price_vendor_reported",
                    "per_reported_value": "41.21",
                    "eps_reported_value": "6564",
                    "pbr_reported_value": "4.23",
                    "bps_reported_value": "63997",
                    "raw_html_sha256": raw_html_sha256,
                    "raw_html_path": raw_html_path,
                    "source_lineage_status": "policy_extracted_reference_snapshot",
                    "missing_policy_fields": "adjusted_price_policy",
                }
            )

    @staticmethod
    def _write_dart_metadata(path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["corp_code", "stock_code", "report_nm", "rcept_no", "rcept_dt"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "corp_code": "00126380",
                    "stock_code": "005930",
                    "report_nm": "FY2025 annual report",
                    "rcept_no": "20260515000001",
                    "rcept_dt": "20260515",
                }
            )

    @staticmethod
    def _write_scores(path: Path) -> None:
        payload = {
            "candidate_id": "sc_v1_5_diag",
            "evidence_id": "ee_v1_5_diag",
            "selector_score": 0.42,
            "selector_score_source": "fixture",
        }
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _write_raw_snapshot(path: Path, *, include_dividend: bool = False) -> None:
        payload = {
            "endpoint_name": "disclosure_list",
            "source_ref": "opendart:disclosure_list:00126380:2026-05-14",
            "raw_json": {
                "list": [
                    {
                        "corp_code": "00126380",
                        "stock_code": "005930",
                        "report_nm": "FY2025 annual report",
                        "rcept_no": "20260310002820",
                        "rcept_dt": "20260310",
                    }
                ]
            },
        }
        financial_payload = {
            "endpoint_name": "single_account",
            "source_ref": "opendart:single_account:00126380:2026-05-14",
            "raw_json": {
                "list": [
                    {
                        "account_nm": "매출액",
                        "bsns_year": "2025",
                        "corp_code": "00126380",
                        "currency": "KRW",
                        "fs_div": "CFS",
                        "fs_nm": "Consolidated",
                        "reprt_code": "11011",
                        "rcept_no": "20260310002820",
                        "sj_div": "IS",
                        "sj_nm": "Income statement",
                        "stock_code": "005930",
                        "thstrm_amount": "1000",
                        "thstrm_dt": "2025.12.31",
                        "thstrm_nm": "FY2025",
                    },
                    {
                        "account_nm": "영업이익",
                        "bsns_year": "2025",
                        "corp_code": "00126380",
                        "currency": "KRW",
                        "fs_div": "CFS",
                        "fs_nm": "Consolidated",
                        "reprt_code": "11011",
                        "rcept_no": "20260310002820",
                        "sj_div": "IS",
                        "sj_nm": "Income statement",
                        "stock_code": "005930",
                        "thstrm_amount": "100",
                        "thstrm_dt": "2025.12.31",
                        "thstrm_nm": "FY2025",
                    },
                    {
                        "account_nm": "당기순이익(손실)",
                        "bsns_year": "2025",
                        "corp_code": "00126380",
                        "currency": "KRW",
                        "fs_div": "CFS",
                        "fs_nm": "Consolidated",
                        "reprt_code": "11011",
                        "rcept_no": "20260310002820",
                        "sj_div": "IS",
                        "sj_nm": "Income statement",
                        "stock_code": "005930",
                        "thstrm_amount": "100",
                        "thstrm_dt": "2025.12.31",
                        "thstrm_nm": "FY2025",
                    }
                ]
            },
        }
        lines = [json.dumps(payload, sort_keys=True), json.dumps(financial_payload, sort_keys=True)]
        if include_dividend:
            dividend_payload = {
                "endpoint_name": "alot_matter",
                "source_ref": "opendart:alot_matter:00126380:2026-05-14",
                "raw_json": {
                    "_request_context": {"code": "005930", "corp_code": "00126380"},
                    "list": [
                        {
                            "corp_code": "00126380",
                            "rcept_no": "20260310002820",
                            "se": "dividend_per_share",
                            "stock_knd": "common",
                            "stlm_dt": "2025-12-31",
                            "thstrm": "1000",
                        }
                    ],
                },
            }
            lines.append(json.dumps(dividend_payload, sort_keys=True))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _write_market_snapshot(path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "schema_version",
                    "as_of_date",
                    "ticker",
                    "shares_outstanding",
                    "source_ref",
                    "average_traded_value_price_source_path",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "schema_version": "fixture",
                    "as_of_date": "2026-05-01",
                    "ticker": "005930",
                    "shares_outstanding": "100",
                    "source_ref": "fixture_market_snapshot",
                    "average_traded_value_price_source_path": "data/005930_daily_prices.csv",
                }
            )

    @staticmethod
    def _write_daily_price(path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["날짜", "종가"])
            writer.writeheader()
            writer.writerow({"날짜": "2026-05-20", "종가": "20"})


if __name__ == "__main__":
    unittest.main()
