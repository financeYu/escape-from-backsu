from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path
from typing import Any


REPORT_FILES = {
    "ingestion": "ingestion_report.md",
    "classification_summary": "classification_summary.csv",
    "source_health": "source_health.md",
    "scholar_discovery": "scholar_discovery_report.md",
    "rejected_items": "rejected_items.md",
    "handoff": "handoff_summary.md",
}


def generate_reports(
    *,
    output_dir: str | Path,
    run_id: str,
    papers: list[dict[str, Any]] | None = None,
    evidence_cards: list[dict[str, Any]] | None = None,
    scholar_seeds: list[dict[str, Any]] | None = None,
    source_health: dict[str, Any] | None = None,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    papers = papers or []
    evidence_cards = evidence_cards or []
    scholar_seeds = scholar_seeds or []
    source_health = source_health or {}

    paths = {key: out / filename for key, filename in REPORT_FILES.items()}
    paths["ingestion"].write_text(render_ingestion_report(run_id, papers, evidence_cards, scholar_seeds), encoding="utf-8")
    write_classification_summary(paths["classification_summary"], evidence_cards)
    paths["source_health"].write_text(render_source_health(run_id, source_health), encoding="utf-8")
    paths["scholar_discovery"].write_text(render_scholar_discovery_report(run_id, scholar_seeds), encoding="utf-8")
    paths["rejected_items"].write_text(render_rejected_items(run_id, evidence_cards), encoding="utf-8")
    paths["handoff"].write_text(render_handoff_summary(run_id, evidence_cards), encoding="utf-8")
    return paths


def render_ingestion_report(
    run_id: str,
    papers: list[dict[str, Any]],
    evidence_cards: list[dict[str, Any]],
    scholar_seeds: list[dict[str, Any]],
) -> str:
    branch_counts = _branch_counts(evidence_cards)
    route_counts = _route_counts(evidence_cards)
    manual_count = sum(1 for card in evidence_cards if card["classification"].get("manual_review_required"))
    retracted_count = sum(1 for paper in papers if paper.get("is_retracted") is True)
    unresolved_seeds = [
        seed
        for seed in scholar_seeds
        if seed.get("canonical_lookup_status") in {"unresolved", "ambiguous", "rejected"}
    ]
    return "\n".join(
        [
            f"# Research Ingestion Report",
            "",
            f"- run_id: `{run_id}`",
            f"- normalized paper count: {len(papers)}",
            f"- EvidenceCard count: {len(evidence_cards)}",
            f"- manual review required: {manual_count}",
            f"- retracted / blocked paper count: {retracted_count}",
            f"- unresolved Scholar seed count: {len(unresolved_seeds)}",
            f"- PDF fulltext used: no",
            "",
            "## 핵심 제한 사항",
            "- 이번 실행은 score 채택을 수행하지 않았습니다.",
            "- 이번 실행은 backtest를 수행하지 않았습니다.",
            "- 논문 claim은 검증된 alpha가 아닙니다.",
            "- valuation 후보는 별도 valuation agent로 handoff해야 합니다.",
            "- Google Scholar snippet, ranking, citation count는 evidence로 사용하지 않았습니다.",
            "",
            "## branch별 분류 건수",
            _counter_lines(branch_counts),
            "",
            "## downstream_route별 건수",
            _counter_lines(route_counts),
            "",
            "## unresolved Scholar seeds",
            _seed_lines(unresolved_seeds),
            "",
            "## 다음 작업 제안",
            "- 수동 검토가 필요한 hybrid / unresolved seed를 먼저 정리합니다.",
            "- technical 후보는 Score Architect에서 별도 score definition으로만 검토합니다.",
            "- valuation 후보는 point-in-time fundamentals 검증 전까지 unavailable로 유지합니다.",
            "",
        ]
    )


def write_classification_summary(path: Path, evidence_cards: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "research_branch",
                "downstream_route",
                "main_score_branch_candidate",
                "count",
            ],
        )
        writer.writeheader()
        counts = Counter(
            (
                card["classification"]["research_branch"],
                card["classification"]["downstream_route"],
                card["classification"]["main_score_branch_candidate"],
            )
            for card in evidence_cards
        )
        for (branch, route, main_branch), count in sorted(counts.items()):
            writer.writerow(
                {
                    "research_branch": branch,
                    "downstream_route": route,
                    "main_score_branch_candidate": main_branch,
                    "count": count,
                }
            )


def render_source_health(run_id: str, source_health: dict[str, Any]) -> str:
    lines = [
        "# Source Health",
        "",
        f"- run_id: `{run_id}`",
        "- API key values are redacted and must not appear in this report.",
        "- rate-limit / 403 / 429 events require conservative retry or manual review.",
        "",
    ]
    if not source_health:
        lines.append("현재 기록된 source health 이벤트가 없습니다.")
    for source, payload in source_health.items():
        lines.append(f"## {source}")
        for key, value in payload.items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def render_scholar_discovery_report(run_id: str, seeds: list[dict[str, Any]]) -> str:
    status_counts = Counter(seed.get("canonical_lookup_status", "unresolved") for seed in seeds)
    lines = [
        "# Scholar Discovery Report",
        "",
        f"- run_id: `{run_id}`",
        "- Google Scholar는 discovery-only입니다.",
        "- 로컬 파일 입력만 처리하며 scholar.google.com live request는 금지됩니다.",
        "- Scholar snippet은 EvidenceCard evidence_snippets_short에 사용하지 않습니다.",
        "",
        "## status counts",
        _counter_lines(status_counts),
        "",
        "## unresolved seeds",
        _seed_lines([seed for seed in seeds if seed.get("canonical_lookup_status") in {"unresolved", "ambiguous", "rejected"}]),
        "",
    ]
    return "\n".join(lines)


def render_rejected_items(run_id: str, evidence_cards: list[dict[str, Any]]) -> str:
    rejected = [
        card
        for card in evidence_cards
        if card["classification"]["downstream_route"] == "reject_log"
        or card["paper"].get("is_retracted") is True
    ]
    lines = ["# Rejected Items", "", f"- run_id: `{run_id}`", ""]
    if not rejected:
        lines.append("현재 reject_log 항목이 없습니다.")
    for card in rejected:
        lines.append(f"- {card['paper'].get('title')} / reason: {card['classification'].get('classification_reason_ko')}")
    lines.append("")
    return "\n".join(lines)


def render_handoff_summary(run_id: str, evidence_cards: list[dict[str, Any]]) -> str:
    by_route = _route_counts(evidence_cards)
    lines = [
        "# Handoff Summary",
        "",
        f"- run_id: `{run_id}`",
        "- EvidenceCards are not adopted scores.",
        "- paper claims are not verified alpha.",
        "- valuation candidates must remain separated from the main technical Score Architect.",
        "",
        "## route counts",
        _counter_lines(by_route),
        "",
    ]
    for route in [
        "technical_score_architect",
        "valuation_agent_handoff",
        "hybrid_split_required",
        "diagnostic_backlog",
        "reject_log",
    ]:
        cards = [card for card in evidence_cards if card["classification"]["downstream_route"] == route]
        lines.append(f"## {route}")
        if not cards:
            lines.append("- 없음")
        for card in cards:
            lines.append(f"- {card['paper'].get('title')} ({card['classification']['research_branch']})")
        lines.append("")
    return "\n".join(lines)


def _branch_counts(cards: list[dict[str, Any]]) -> Counter:
    return Counter(card["classification"]["research_branch"] for card in cards)


def _route_counts(cards: list[dict[str, Any]]) -> Counter:
    return Counter(card["classification"]["downstream_route"] for card in cards)


def _counter_lines(counter: Counter) -> str:
    if not counter:
        return "- 없음"
    return "\n".join(f"- {key}: {counter[key]}" for key in sorted(counter))


def _seed_lines(seeds: list[dict[str, Any]]) -> str:
    if not seeds:
        return "- 없음"
    return "\n".join(f"- {seed.get('raw_title')} ({seed.get('canonical_lookup_status')})" for seed in seeds)
