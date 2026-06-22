# Default workflows

## Doing tasks

1. **Plan** non-trivial work with TodoWrite (3+ steps, or multiple files).
   Keep exactly one task `in_progress`; mark items `completed` the moment
   they're done — don't batch completions.
2. **Gather context before acting.** Read the relevant files; for open-ended
   exploration use a sub-agent rather than many direct searches.
3. **Make the change**, following @coding-style.md.
4. **Verify** with the project's own commands (build / tests / lint) before
   claiming completion. Evidence before assertions.
5. **Wrap up** — run the `wrap-up` skill to capture any durable lesson.

## TodoWrite usage

- Use it for multi-step or multi-file work, and to give the user visibility.
- Skip it for single trivial steps.
- Re-plan freely as new information arrives; the list is a working artifact.

## Verification discipline

- Never claim "done", "fixed", or "passing" without having run the command
  that proves it and seen the output.
- If you cannot verify, say so explicitly rather than implying success.

## Sub-agents and parallelism

- Dispatch independent units of work to parallel sub-agents when they share no
  state and have no sequential dependency.
- For consequential artifacts about to be reused/propagated, consider a
  verification council (see `playbooks/ai-assisted-coding/verification-council.md`):
  divergent-mandate reviewers (evidence-verifier + adversarial) that must check
  claims against authoritative sources before the artifact propagates.
