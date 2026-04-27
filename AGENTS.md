1. Read `docs/root_hard_stops.md` and `docs/roadmap_status.md` before every task; read nothing else by default.
2. Treat `docs/root_hard_stops.md` as project authority and `docs/roadmap_status.md` as current route state.
3. Treat the user prompt as this gate's local goal/output only; reusable rules live in docs or skills.
4. Classify as `planning/read-only`, `narrow edit`, or `Step/gate closure`, then route to the narrowest project and Codex skill gate; before any sub-agent executes, root must name the matching skill gate and provide current task, allowed scope, forbidden scope, required output, validation commands, and Korean final report format.
5. For candidate ML/probability gate work, use `.agents/skills/quant-candidate-ml-gate/SKILL.md` and run its contract validator when applicable.
6. For Quant subproject-wide audit/scope-watchdog work, use `.agents/skills/quant-subproject-audit-gate/SKILL.md`; keep audit verdict and validation evidence as separate parts.
7. For subproject work, read only that subproject `AGENTS.md`, one active packet, one needed domain stub, and targeted files.
8. Obey hard stops: no universe/data-ingestion expansion, active valuation/fundamental scoring, ranking/report/backtest semantic change, trading advice, or final score replacement unless explicitly authorized.
9. Use separate role worktrees/branches for Step 15+ implementation, review, audit, research, chart runtime, and master integration work.
10. Do not read archives, generated outputs, raw data, caches, charts, logs, or release evidence unless a named conflict/regression/provenance/release check requires it.
11. Report gate endings as `COMPLETE`, `PARTIALLY COMPLETE`, or `NEEDS FIX`; run `.agents/skills/quant-review-gate/SKILL.md` before accepting completion, and use `.agents/skills/quant-git-finalize/SKILL.md` only after review gate `PASS`; do not commit before required validation/review is complete.
