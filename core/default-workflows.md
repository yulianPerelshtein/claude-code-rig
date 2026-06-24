# Default workflows

## Doing tasks

1. **Plan** non-trivial work (3+ steps, or multiple files) with TodoWrite —
   skip it for single trivial steps. Keep exactly one task `in_progress`; mark
   items `completed` the moment they're done. Re-plan freely as new information
   arrives; the list is a working artifact, and gives the user visibility.
2. **Gather context before acting.** Read the relevant files; for open-ended
   exploration use a sub-agent rather than many direct searches.
3. **Make the change.**
4. **Verify** with the project's own commands (build / tests / lint) before
   claiming completion. Evidence before assertions.
5. **Wrap up** — when a session surfaces a durable lesson, capture it with
   `/wrap-up`.

## Tool usage

- Prefer absolute paths over `cd <dir> && <cmd>` — the latter can trigger a
  permission prompt.

## Verification discipline

- Never claim "done", "fixed", or "passing" without having run the command
  that proves it and seen the output.
- If you cannot verify, say so explicitly rather than implying success.

## Sub-agents and parallelism

- Dispatch independent units of work to parallel sub-agents when they share no
  state and have no sequential dependency.
- For consequential artifacts about to be reused/propagated, run the
  `verification-council` skill: divergent-mandate reviewers (evidence-verifier +
  adversarial) that check claims against authoritative sources before the
  artifact propagates.
