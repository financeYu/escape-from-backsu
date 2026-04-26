# Post-MVP Agent Task Packet

This sidecar defines the compact task format for subproject workers after the
Step 20 MVP v0.1 freeze-ready baseline. It is a routing aid and does not
override `AGENTS.md`, `docs/project_checklist.md`, `docs/roadmap_status.md`, or
the user's latest explicit instruction.

Use this packet when root/master delegates post-MVP work to `Quant_mvp`,
`reserch_mvp`, `chart_mvp`, `review_mvp`, or a scoped support worker.

## Packet Template

```text
You are working after Step 20 completion for MVP v0.1 freeze.

Confirmed facts, max 3:
1. Step 20 is complete and MVP v0.1 is freeze-ready.
2. The MVP v0.1 baseline is KOSPI200-only and technical-only.
3. Completed Step 1-20 history and old roadmap are archive-only.

Current task:
<concrete task here>

Scope:
- Work from the current MVP v0.1 baseline, not the old roadmap.
- Route through `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`,
  `docs/context/EXTENSION_REGISTRY.toml`, and
  `docs/context/CHANGE_IMPACT_MATRIX.yml` when contract, extension, or impact
  classification is needed.
- Prefer additive sidecar files.
- Do not modify quant logic, score formulas, ranking behavior, report behavior,
  backtest behavior, valuation activation, or data ingestion unless this
  concrete post-MVP task explicitly assigns that scope.
- Do not implement future extensions unless explicitly requested in a later
  approved post-MVP step.

Archive lookup rule:
Start from `docs/context/ARCHIVE_INDEX.md`. Only inspect archive/history files
for regression, provenance, or freeze verification. Do not summarize or import
old Step history into active context.

Required Korean final report:
1. 변경 요약
2. 변경 파일
3. 검증 결과
4. MVP v0.1 기준선 훼손 여부
5. 남은 리스크
6. 다음 작업 가능 범위
```

## Worker Rules

- If `Current task` is blank, stop and ask for the concrete task before editing.
- Keep confirmed facts to three or fewer.
- Read only the active packet, required authority files, and targeted files for
  the requested work.
- Do not read archives, generated packets, validation logs, runtime reports, raw
  market data, caches, or chart images unless the packet names a regression,
  provenance, freeze verification, or release-evidence need.
- If an exception is justified, read the narrowest file needed and state the
  reason in the final report.
- If the request appears to require a subproject boundary crossing, root-owned
  policy edit, runtime behavior change, score/ranking/report/backtest change,
  valuation activation, or data-ingestion change outside the assigned scope,
  stop and report the needed approval instead of implementing.
- Use the required Korean final report sections even when the work is read-only.
