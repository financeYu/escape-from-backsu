---
name: workspace-ml-env
description: Use when running or adding local ML selectors, model comparisons, trainability checks, or ML dependency validation in master_mvp or Quant subprojects; pins all ML work to the root .venv and records package availability without weakening evidence-only guardrails.
---

# Workspace ML Environment

Use this skill for project-local ML work in `master_mvp` and its subprojects.
It is an environment and dependency contract only. It does not authorize live
trading, order generation, production ranking replacement, valuation activation,
new data ingestion, or future-return claims.

## Required Interpreter

Run ML checks from the repository root with the root workspace interpreter:

```powershell
.venv\Scripts\python.exe
```

Subprojects such as `Quant_mvp`, `Quant_mvp/research_mvp`, `chart_mvp`, and
`review_mvp` must not create separate ML virtual environments for Codex tasks.

## Environment Variables

The project Codex config should expose:

```text
PROJECT_ML_PYTHON=C:\Users\jjaew\Project\master_mvp\.venv\Scripts\python.exe
PROJECT_ML_REQUIRED_PACKAGES=numpy,pandas,sklearn
PROJECT_ML_OPTIONAL_PACKAGES=lightgbm,xgboost,catboost
PROJECT_ML_THREAD_COUNT=1
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
LOKY_MAX_CPU_COUNT=1
```

Required packages must be importable before an ML selector task can claim
trainability. Optional packages may be unavailable, but model manifests must
record each unavailable package as skipped rather than silently replacing it.

## Dependency Contract

Root `pyproject.toml` owns the shared ML dependency set through the `ml`
optional extra. `requirements-dev.txt` mirrors those local dependencies as
direct install lines and avoids editable local project installs, because the
root workspace and local subproject sources are made importable for Codex
through `.codex/config.toml` `PYTHONPATH`.

Current local tabular ML package set:

- required: `numpy`, `pandas`, `scikit-learn`
- optional challenger families: `lightgbm`, `xgboost`, `catboost`

## Selector Guardrails

ML outputs remain evidence-only and manual-review-support only. Model output
may be used for `AdoptionCandidate` review prioritization comparisons only.
It must not update `technical_composite_score`, `final_composite_score`, live
runtime rankings, trading instructions, order generation, or production
behavior.

Every selector implementation must keep:

- feature and label manifests separated
- no-lookahead and leakage checks explicit
- time-ordered validation rather than random split
- missing optional ML packages recorded in model manifests
- model comparison framed as historical or simulated evidence review support

## Validation

Run:

```powershell
.venv\Scripts\python.exe .agents/skills/workspace-ml-env/scripts/validate_workspace_ml_env.py --format text
```

Use `--require-optional` only when the task explicitly requires every optional
ML package to be importable in the current local environment.

## Output

Report in Korean with:

```yaml
gate: workspace_ml_env
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
required_packages:
  - "<package: present|missing>"
optional_packages:
  - "<package: present|missing>"
environment:
  - "<variable: value or missing>"
validation:
  - "<command: pass/fail>"
remaining_risk:
  - "<none or compact risk>"
```
