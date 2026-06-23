---
name: project-journal
description: >-
  Disciplined working-notes for a multi-stage project: a stage-gated plan with a
  resumption protocol, a numbered decision log (rationale + alternatives + divergences),
  a revise-later parking lot, and per-project agent conventions. Use when a project
  carries a PLAN.md / thought-process.md / decisions log / AGENTS.md.
paths:
  - "**/PLAN.md"
  - "**/thought-process.md"
  - "**/decisions*.md"
  - "**/revise-later.md"
  - "**/AGENTS.md"
---

# Project journal

A multi-stage project benefits from a small set of private working-notes files
that carry the *reasoning* a git history can't: why each non-obvious choice was
made, what was rejected, where reality diverged from the plan, and how to resume
cleanly after a context clear. This is a **discipline, not a template** — each
artifact earns its keep only when the project is large enough to forget its own
decisions. Don't spawn the full set for a one-afternoon change.

These are working-notes files: keep the journal variants (the plan, the design
notes, the parking lot) gitignored and unreferenced from tracked files (see
`project-conventions.md`). They are distilled into a final report or PR
description when the work ships — not committed raw. (A *tracked* ADR-style
`decisions/` log is a different artifact and follows your repo's normal commit
rules.)

Read the topic file relevant to the task:

- `stage-gated-plan.md` — plan structure: context → scope → stages with
  checkpoints → risk register → resumption protocol; closes with the
  synthesis-report shape.
- `decision-log.md` — numbered decisions (statement + rationale +
  alternatives-rejected), divergences captured at the moment of discovery, and
  the Structured Finding Format for evidence-backed notes.
- `revise-later.md` — the deferred-learning parking lot that keeps momentum
  without losing rigor.
- `project-conventions.md` — per-project `AGENTS.md` layered on global rules.

See also: `domains/methodology/derivation-not-templating.md` (why this is
discipline rather than a generator) and
`domains/methodology/living-docs-update-policy.md` (when a living doc earns an
update vs. stays put).
