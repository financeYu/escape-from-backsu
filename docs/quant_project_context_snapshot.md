# Quant Project Context Snapshot

This workspace keeps one compact local context snapshot for the current Quant
project:

```text
quant_project_reference_for_chatgpt_project_current.md
```

Step-end automation may run this local-only command after validation, review,
required fixes, rerun, and commit:

```powershell
python scripts/refresh_quant_project_context.py
```

The command:

- regenerates the compact latest context file
- removes obsolete local context versions listed in `Quant_mvp/config/context_snapshot.toml`
- performs no OpenAI API call and no paid upload

The context is intentionally compact and source-controlled as the latest project
reference. Do not include secrets, `.env`, runtime caches, generated chart
images, or raw data caches in the snapshot.

