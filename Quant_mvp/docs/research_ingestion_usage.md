# Research Ingestion Usage

Research ingestion is now owned and executed inside `Quant_mvp`:

```text
Quant_mvp/research_mvp
```

Run the CLI from the repository root after editable install:

```powershell
python -m pip install -e .\Quant_mvp\research_mvp
python -m research_ingestion --help
```

Or run it without install by setting the research package path from the
repository root:

```powershell
$env:PYTHONPATH='Quant_mvp\research_mvp\src'
python -m research_ingestion --help
```

Use `Quant_mvp/research_mvp/AGENTS.md` for runnable research-ingestion
commands and guardrails. Use `Quant_mvp/config/research_intake.toml` for the
score-governance lane's EvidenceCard intake contract.

Boundary reminders:

- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Scholar seeds are discovery inputs only.
- Financial/fundamental data must not enter `technical_composite_score` or
  `final_composite_score`.
