# master_mvp

Git-first workspace for coordinating the KOSPI200 research, quant-design, and scanner-runtime MVPs.

## Projects

| Project | Role | Main agent/document |
| --- | --- | --- |
| `reserch_mvp` | Research-ingestion specification and evidence preparation | `reserch_mvp/AGENTS.md` |
| `Quant_mvp` | Score design, config policy, technical review, valuation boundary | `Quant_mvp/AGENTS.md` |
| `chart_mvp` | Executable scanner, data cache, chart rendering, CLI, GUI | `chart_mvp/AGENTS.md` |
| `review_mvp` | Code-review tooling, minimal repair policy, final validation support | `review_mvp/AGENTS.md` |

## Why this structure

The workspace separates research evidence, score governance, runtime implementation, and final code review so each change has a clear owner. This keeps Git diffs reviewable, prevents generated data from becoming source code, and reduces the risk of mixing valuation claims into price-only technical logic.

Read `AGENTS.md` first, then the relevant subproject `AGENTS.md`.

## Git policy

Commit code, docs, tests, config, and small reference fixtures.

Do not commit local caches, generated chart images, scan outputs, virtual environments, bytecode, or secrets.

See `docs/project_registry.md` for the current project map and handoff rules.
