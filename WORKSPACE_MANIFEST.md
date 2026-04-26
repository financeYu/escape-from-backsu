# Workspace Manifest

## Role

GUI integration worker for post-MVP `gui_mvp` consolidation.

## Branch

`codex/step21-gui-mvp-unified-tabs`

## Allowed Write Scope

- `gui_mvp/**`
- `tests/gui_mvp/**`
- `WORKSPACE_MANIFEST.md`

## Guardrails

- Keep Quant backtest semantics unchanged.
- Keep chart scanner semantics unchanged.
- Do not feed backtest results into scoring, ranking, reports, or config.
- Do not commit generated reports, caches, chart images, market data, or local outputs.

## Validation Profile

Minimal focused validation:

```powershell
python -m pytest -q -p no:cacheprovider tests/gui_mvp
```
