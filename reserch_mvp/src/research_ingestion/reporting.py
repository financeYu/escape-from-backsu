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
    collection_summary: dict[str, Any] | None = None,
    enrichment_summary: dict[str, Any] | None = None,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    papers = papers or []
    evidence_cards = evidence_cards or []
    scholar_seeds = scholar_seeds or []
    source_health = source_health or {}
    collection_summary = collection_summary or {}
    enrichment_summary = enrichment_summary or collection_summary.get("enrichment", {})

    paths = {key: out / filename for key, filename in REPORT_FILES.items()}
    paths["ingestion"].write_text(
        render_ingestion_report(run_id, papers, evidence_cards, scholar_seeds, collection_summary, enrichment_summary),
        encoding="utf-8",
    )
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
    collection_summary: dict[str, Any] | None = None,
    enrichment_summary: dict[str, Any] | None = None,
) -> str:
    collection_summary = collection_summary or {}
    enrichment_summary = enrichment_summary or collection_summary.get("enrichment", {})
    branch_counts = _branch_counts(evidence_cards)
    route_counts = _route_counts(evidence_cards)
    manual_count = sum(1 for card in evidence_cards if card["classification"].get("manual_review_required"))
    retracted_count = sum(1 for paper in papers if paper.get("is_retracted") is True)
    raw_counts = collection_summary.get("raw_records_collected_by_source", {})
    relevance_rejected = collection_summary.get("records_rejected_by_relevance", 0)
    relevance_manual_review = collection_summary.get("records_manual_review_by_relevance", 0)
    enrichment_counts = enrichment_summary.get("enriched_records_by_source", {})
    enrichment_target_count = enrichment_summary.get("target_count", 0)
    selected_sources = collection_summary.get("selected_sources", [])
    selected_query_set = collection_summary.get("selected_query_set")
    run_timestamp = collection_summary.get("timestamp_utc")
    rejected_count = sum(1 for card in evidence_cards if card["classification"].get("downstream_route") == "reject_log")
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
            f"- run timestamp: `{run_timestamp or 'unknown'}`",
            f"- selected sources: {', '.join(selected_sources) if selected_sources else 'unknown'}",
            f"- selected query-set: `{selected_query_set or 'unknown'}`",
            f"- raw records by source: {_inline_mapping(raw_counts)}",
            f"- collection relevance rejected: {relevance_rejected}",
            f"- collection relevance manual review: {relevance_manual_review}",
            f"- enrichment target count: {enrichment_target_count}",
            f"- enrichment records by source: {_inline_mapping(enrichment_counts)}",
            f"- normalized paper count: {len(papers)}",
            f"- deduped paper count: {len(papers)}",
            f"- EvidenceCard count: {len(evidence_cards)}",
            f"- rejected item count: {rejected_count}",
            f"- manual review required: {manual_count}",
            f"- retracted / blocked paper count: {retracted_count}",
            f"- unresolved Scholar seed count: {len(unresolved_seeds)}",
            f"- PDF fulltext used: no",
            "",
            "## source freshness / currentness",
            "- source health는 해당 run_id 실행 시점의 snapshot이며 현재 vendor availability 검증이 아닙니다.",
            "- cache hit 또는 stale record는 research 후보 관리용 metadata이며 MVP scoring 입력이 아닙니다.",
            "- research source freshness는 `technical_composite_score`, `final_composite_score`, ranking 순서를 변경하지 않습니다.",
            "",
            "## 핵심 제한 사항",
            "- 이번 실행은 score 채택을 수행하지 않았습니다.",
            "- 이번 실행은 backtest를 수행하지 않았습니다.",
            "- 논문 claim은 검증된 alpha가 아닙니다.",
            "- valuation 후보는 별도 valuation agent로 handoff해야 합니다.",
            "- Google Scholar snippet, ranking, citation count는 evidence로 사용하지 않았습니다.",
            "- EvidenceCard는 score 채택이 아니며, 논문 claim은 검증된 alpha가 아닙니다.",
            "",
            "## branch별 분류 건수",
            _counter_lines(branch_counts),
            "",
            "## downstream_route별 건수",
            _counter_lines(route_counts),
            "",
            "## source 오류 / rate-limit 요약",
            _source_health_lines(collection_summary, enrichment_summary),
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
                "count",
                "manual_review_count",
            ],
        )
        writer.writeheader()
        counts = Counter(
            (
                card["classification"]["research_branch"],
                card["classification"]["downstream_route"],
            )
            for card in evidence_cards
        )
        manual_counts = Counter(
            (
                card["classification"]["research_branch"],
                card["classification"]["downstream_route"],
            )
            for card in evidence_cards
            if card["classification"].get("manual_review_required")
        )
        for (branch, route), count in sorted(counts.items()):
            writer.writerow(
                {
                    "research_branch": branch,
                    "downstream_route": route,
                    "count": count,
                    "manual_review_count": manual_counts[(branch, route)],
                }
            )


def render_source_health(run_id: str, source_health: dict[str, Any]) -> str:
    lines = [
        "# Source Health",
        "",
        f"- run_id: `{run_id}`",
        "- freshness scope: 이 보고서는 해당 run_id 실행 시점의 source-health snapshot입니다.",
        "- currentness warning: 이 파일만으로 현재 vendor availability, API freshness, 또는 최신 연구 검증을 증명하지 않습니다.",
        "- MVP boundary: source-health, cache hit, stale cache 상태는 MVP scoring/ranking 입력이 아닙니다.",
        "- API key 값은 redaction 대상이며 이 보고서에 노출되면 안 됩니다.",
        "- rate-limit / 403 / 429 이벤트는 보수적 retry 또는 수동 검토가 필요합니다.",
        "",
    ]
    lines.extend(_source_health_cache_lines(source_health))
    if not source_health:
        lines.append("현재 기록된 source health 이벤트가 없습니다.")
    for source, payload in source_health.items():
        lines.append(f"## {source}")
        for key, value in payload.items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def _source_health_cache_lines(source_health: dict[str, Any]) -> list[str]:
    cache_hit_count = 0
    cache_miss_count = 0
    cache_stale_count = 0
    for payload in source_health.values():
        if not isinstance(payload, dict):
            continue
        cache_hit_count += int(payload.get("request_cache_hit_count") or 0)
        cache_miss_count += int(payload.get("request_cache_miss_count") or 0)
        cache_stale_count += int(payload.get("request_cache_stale_count") or 0)
    lines = [
        f"- request cache hits: {cache_hit_count}",
        f"- request cache misses: {cache_miss_count}",
        f"- stale cache observations: {cache_stale_count}",
    ]
    if cache_stale_count:
        lines.append("- stale cache warning: stale cache가 관찰되면 current validated input으로 해석하지 말고 재수집 또는 수동 검토가 필요합니다.")
    return lines + [""]


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
        "- EvidenceCard는 adopted score가 아닙니다.",
        "- 논문 claim은 검증된 alpha가 아닙니다.",
        "- valuation 후보는 main technical Score Architect와 분리해야 합니다.",
        "- downstream agent가 구현 전 EvidenceCard와 제한 사항을 다시 검토해야 합니다.",
        "- source-health freshness는 handoff 참고 정보이며 MVP scoring/ranking 입력이 아닙니다.",
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


def _inline_mapping(mapping: dict[str, Any]) -> str:
    if not mapping:
        return "없음"
    return ", ".join(f"{key}={value}" for key, value in sorted(mapping.items()))


def _source_health_lines(collection_summary: dict[str, Any], enrichment_summary: dict[str, Any]) -> str:
    lines: list[str] = []
    for label, summary in [("collect", collection_summary), ("enrich", enrichment_summary)]:
        if not summary:
            continue
        target_count = summary.get("target_count")
        if target_count is not None:
            lines.append(f"- {label}: target_count={target_count}, enriched_records={summary.get('enriched_records_written', 0)}")
        plan = summary.get("plan", {})
        if plan.get("offline"):
            lines.append(f"- {label}: offline mode로 network call을 수행하지 않았습니다.")
    return "\n".join(lines) if lines else "- 기록된 오류/rate-limit 요약이 없습니다. 자세한 내용은 source_health.md를 확인하세요."


def _seed_lines(seeds: list[dict[str, Any]]) -> str:
    if not seeds:
        return "- 없음"
    return "\n".join(f"- {seed.get('raw_title')} ({seed.get('canonical_lookup_status')})" for seed in seeds)
