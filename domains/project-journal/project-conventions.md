# Per-project conventions (AGENTS.md)

A project-local `AGENTS.md` layers project-specific rules on top of your global
conventions. It captures the handful of rules that are true *here* and would be
wrong as global defaults — the naming scheme, the toolchain quirk, the one file
that must never be referenced from tracked code.

## What earns a place

Keep it short and specific. Rules worth pinning per-project:

- **Working-notes hygiene.** The plan / design-notes / parking-lot files are
  gitignored and **never referenced from tracked files** (code, comments,
  README, configs). A reference from tracked source to a private working doc
  creates a dangling pointer for anyone who clones the repo and leaks the
  internal notes structure. References *between* the private notes are fine.
- **Review checkpoint before commit batches.** Before any git activity, list the
  files, summarize the changes, and surface decisions made during execution —
  then wait for an explicit go-ahead. This is the per-project echo of the
  stage checkpoint.
- **Surface decision-affecting questions early.** When a non-obvious choice
  comes up mid-execution, raise it *before* acting on it, not as a fait
  accompli presented after the fact.
- **Naming / layout facts** that recur: distribution vs. import name, the CLI
  entry point, which lockfile is tracked vs. ignored.

## Why a separate file

These rules are too project-specific for global instructions and too
load-bearing to leave implicit. An `AGENTS.md` makes them explicit and reviewable
without polluting either the global config or the tracked codebase. It is itself
a working-notes file — keep it gitignored unless the project deliberately ships
agent guidance to collaborators.

The "no LLM-flavored prose" rule belongs here too: comments and docs should read
as if a careful human wrote them by hand — no rhetorical capitalization, no
"as discussed" / "per the plan" framing, no chatty rationales. See
`domains/methodology/living-docs-update-policy.md` for when these notes earn an
update.
