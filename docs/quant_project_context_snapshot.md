# Quant Project Context Snapshot

This workspace keeps one compact local context snapshot for the current Quant
project:

```text
docs/context/gpt/quant_project_reference_for_chatgpt_project_current.md
```

Run this local-only command only when the user explicitly requests a ChatGPT
reference refresh:

```powershell
python scripts/refresh_quant_project_context.py --user-requested
```

The separate GPT submission brief is also request-gated:

```powershell
python scripts/context/build_context_packet.py --mode gpt-brief --user-requested --request "<current GPT task>"
```

The command:

- regenerates the compact latest context file
- removes obsolete local context versions listed in `Quant_mvp/config/context_snapshot.toml`
- performs no OpenAI API call and no paid upload

The context is intentionally compact and source-controlled as the latest project
reference. Do not include secrets, `.env`, runtime caches, generated chart
images, or raw data caches in the snapshot.
