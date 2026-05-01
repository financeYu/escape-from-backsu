---
name: quant-validator-approval
description: Use after cost-aware-review-refactor records a blocked required validator caused by unavailable bash/WSL or Git Bash Win32 error 5. Preserves narrow exact-command approval paths for project-local quant gate validators, including `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`.
---

# Quant Validator Approval

## Purpose

Run a required project-local quant gate validator without broadening shell
approval after the cost-aware utility has recorded the bash/WSL/Git Bash
blocker. This skill does not authorize new quant behavior; it only
standardizes the approval path for exact validator commands.

## Scope

Allowed:

- project-local quant gate validation commands under `.agents/skills/*/scripts/`
- the exact validator command recorded by `cost-aware-review-refactor`
- escalation only for the exact validator command after sandboxed bash/WSL or
  Git Bash fails with `Win32 error 5`, when that error is already established
  for the current environment, or when the user explicitly asks to avoid or
  persist the known validator approval path
- Quant_mvp subproject validator handoffs that preserve the exact
  root-relative validator command and affected subproject scope

Forbidden:

- broad `bash`, `python`, `powershell`, or repository-wide approval prefixes
- changing validator semantics to bypass the contract
- ranking/report/backtest score behavior changes
- trading, profitability, alpha-proof, or expected-return wording

## Procedure

1. Read `docs/root_hard_stops.md` and `docs/roadmap_status.md` first.
2. Use `.agents/skills/cost-aware-review-refactor/SKILL.md` first to record
   the blocked command, short error, affected scope, substitute evidence when
   available, and routed validator request. Do not jump directly from a failed
   bash/WSL/Git Bash command to escalation.
3. If the work is candidate ML gate work, use
   `.agents/skills/quant-candidate-ml-gate/SKILL.md`.
4. For Quant_mvp subproject work, keep the validator command root-relative
   from `C:\Users\jjaew\Project\master_mvp`. The subproject worker records the
   affected Quant scope and the exact command; root runs or escalates only that
   same command. Do not rewrite the validator, switch to a broader shell
   prefix, or approve a subproject-local Python or bash launcher as a
   substitute.
5. If `Win32 error 5` or unavailable bash/WSL has not already been observed in
   the current environment and the user has not explicitly asked to avoid the
   known sandbox failure, run the validator normally:

   ```bash
   bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh
   ```

6. If the sandboxed run prints WSL installation/update output, Git Bash
   `Win32 error 5`, `couldn't create signal pipe`, or `CreateFileMapping`, or if
   the error is already established for the current environment, or if the user
   explicitly asks to avoid the known sandbox failure, run the same validator
   with `sandbox_permissions: "require_escalated"` and an exact prefix rule.
   For the candidate ML validator, use:

   ```json
   ["bash", ".agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh"]
   ```

   For another project-local gate validator, use the same exact-command shape,
   for example:

   ```json
   ["bash", ".agents/skills/quant-review-gate/scripts/validate_review_gate.sh"]
   ```

   or the exact Git Bash executable plus script path when PowerShell must call
   Git Bash directly:

   ```json
   ["C:\\Program Files\\Git\\bin\\bash.exe", ".agents/skills/quant-review-gate/scripts/validate_review_gate.sh"]
   ```

7. Do not ask a separate chat question before the escalation request. Put the
   approval question in the tool `justification` field so the user can allow or
   persist this exact prefix for future validator runs.
8. Treat validation as passed only when stdout includes the validator's expected
   PASS line, such as:

   ```text
   PASS: quant candidate ML gate contract is present
   ```

## Output

Report in Korean:

```yaml
gate: quant_validator_approval
task_class: planning/read-only | narrow edit | Step/gate closure
blocked_source: "cost-aware-review-refactor summary required"
validator_command: "<exact validator command>"
approval_prefix: "<exact prefix only>"
contract_validation: pass | fail | not_run
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```
