# AI / Copilot review skepticism

Apply critical thinking to AI-generated PR review comments before acting:

- Many are **stale-description nits** requiring zero code change.
- A minority identify real bugs.
- Verify each comment against the codebase's existing patterns and the actual
  runtime behaviour before applying it.

Do not reflexively apply all suggestions — a wrong "fix" applied to satisfy a
bot comment is worse than the comment. Treat the reviewer (human or AI) as a
source of candidate issues, not a source of truth.
