# Cherry-pick / rebase layered PRs

When multiple PRs touch the same files and must be rebased onto a new `main`
that already contains earlier PRs' changes:

- Resolve each conflict by **combining both sides**: take the semantic intent
  from the cherry-picked commit AND keep the fixes that landed in `main` via
  other PRs.
- Never blindly accept one side. For each conflict ask: *what is the correct
  final state given ALL changes that have landed?*
- Re-run the relevant tests after each resolved file, not just at the end.
