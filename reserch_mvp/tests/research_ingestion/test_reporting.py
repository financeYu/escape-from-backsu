from __future__ import annotations

from pathlib import Path

from research_ingestion.classify import classify_paper
from research_ingestion.config import load_research_config
from research_ingestion.evidence import generate_evidence_card
from research_ingestion.reporting import generate_reports, render_ingestion_report


def test_korean_report_generation(sample_paper, workspace_tmp_path):
    paper = sample_paper()
    config = load_research_config(Path(__file__).resolve().parents[2])
    classification = classify_paper(paper, config["classification"], config["policy"])
    card = generate_evidence_card(paper, classification, "run")
    paths = generate_reports(output_dir=workspace_tmp_path, run_id="run", papers=[paper], evidence_cards=[card], scholar_seeds=[])
    text = paths["ingestion"].read_text(encoding="utf-8")
    assert "이번 실행은 score 채택을 수행하지 않았습니다" in text
    assert "논문 claim은 검증된 alpha가 아닙니다" in text
    assert paths["classification_summary"].exists()


def test_report_separates_branch_counts(sample_paper):
    paper = sample_paper()
    config = load_research_config(Path(__file__).resolve().parents[2])
    classification = classify_paper(paper, config["classification"], config["policy"])
    card = generate_evidence_card(paper, classification, "run")
    text = render_ingestion_report("run", [paper], [card], [])
    assert "branch별 분류 건수" in text
    assert "technical" in text
