# Research Ingestion Intake Pointer

Research ingestion is no longer owned or executed from `Quant_mvp`.

The canonical source collection, Scholar discovery import, normalization, classification, EvidenceCard generation, and Korean ingestion reports now live in:

```text
../reserch_mvp
```

Run the CLI from the repository root after editable install:

```powershell
python -m pip install -e .\reserch_mvp
python -m research_ingestion --help
```

Or run it without install by setting the research package path from the repository root:

```powershell
$env:PYTHONPATH='reserch_mvp\src'
python -m research_ingestion --help
```

`Quant_mvp` only owns downstream EvidenceCard intake policy. Use `Quant_mvp/config/research_intake.toml` for the import contract and use `../reserch_mvp/AGENTS.md` for runnable research ingestion commands.

Boundary reminders:

- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Scholar seeds are discovery inputs only.
- Financial/fundamental data must not enter `technical_composite_score` or `final_composite_score`.
