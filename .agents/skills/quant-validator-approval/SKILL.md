---
name: quant-validator-approval
description: Use when the master_mvp quant candidate ML gate contract validator must run through Git Bash and sandboxed bash fails with Win32 error 5, or when Codex needs to avoid a known repeat sandbox failure or repeated approval prompts for the exact validator command. This skill preserves the narrow approved command prefix for `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`.
---

# Quant Validator Approval

## Purpose

Run the required candidate ML gate contract validator without broadening shell
approval. This skill does not authorize new quant behavior; it only standardizes
the approval path for the existing validator.

## Scope

Allowed:

- candidate ML gate contract validation only
- the exact validator command below
- escalation only for the exact validator command after sandboxed Git Bash fails
  with `Win32 error 5`, when that error is already established for the current
  environment, or when the user explicitly asks to avoid or persist the known
  validator approval path

Forbidden:

- broad `bash`, `python`, `powershell`, or repository-wide approval prefixes
- changing validator semantics to bypass the contract
- ranking/report/backtest score behavior changes
- trading, profitability, alpha-proof, or expected-return wording

## Procedure

1. Read `docs/root_hard_stops.md` and `docs/roadmap_status.md` first.
2. If the work is candidate ML gate work, use
   `.agents/skills/quant-candidate-ml-gate/SKILL.md`.
3. If `Win32 error 5` has not already been observed in the current environment
   and the user has not explicitly asked to avoid the known sandbox failure, run
   the validator normally:

   ```bash
   bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh
   ```

4. If the sandboxed run prints Git Bash `Win32 error 5`, or if the error is
   already established for the current environment, or if the user explicitly
   asks to avoid the known sandbox failure, run the same command with
   `sandbox_permissions: "require_escalated"` and this exact prefix rule:

   ```json
   ["bash", ".agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh"]
   ```

5. Do not ask a separate chat question before the escalation request. Put the
   approval question in the tool `justification` field so the user can allow or
   persist this exact prefix for future validator runs.
6. Treat validation as passed only when stdout includes:

   ```text
   PASS: quant candidate ML gate contract is present
   ```

## Output

Report in Korean:

```yaml
gate: quant_validator_approval
task_class: planning/read-only | narrow edit | Step/gate closure
validator_command: "bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh"
approval_prefix: '["bash", ".agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh"]'
contract_validation: pass | fail | not_run
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```
