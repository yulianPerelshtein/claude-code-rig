# Living-docs update policy

A curated knowledge doc (architecture map, decision log, project journal) is a
**living map, not exhaustive change-tracking**. The goal is decision-making, not
coverage. Most edits to a codebase should *not* touch it — otherwise the doc
becomes noise and stops being read. The discipline is knowing when an update
earns its place.

## Update when… / do NOT update for…

**Update when the change moves something a future reader reasons about:**

- An architectural boundary changes — a module moves, a seam/interface is added
  or removed, responsibility ownership shifts.
- A domain concept changes — a new entity, a renamed field, a schema migration.
- Behaviour that is correctness-load-bearing changes — a rule, a coefficient, a
  stage in a pipeline.
- Before a major handoff or milestone.

**Do NOT update for:**

- Styling, formatting, copy tweaks.
- Dependency bumps with no architectural effect.
- Mechanical refactors that don't change responsibility or behaviour.
- Bug fixes that don't reveal an architectural gap.

The test: *if an update would only add noise, skip it; if a future engineer
would be confused without it, write it.*

## Writing discipline for the entries you do make

- **Cite evidence.** Every architectural claim names a file path (and symbol /
  line range where it helps). A claim with no path is a vibe, not a fact.
- **Label confidence** — `High | Medium | Low` — so a later red-team pass knows
  where to spend scrutiny. See `domains/project-journal/decision-log.md` for the
  Structured Finding Format this pairs with.
- **Link, don't duplicate.** A relative-link graph between docs beats restating
  the same fact in three places; the graph is the navigation.

## Why this is a policy, not an automation

A standing temptation is to build a parallel knowledge system — routines that
crawl repos, regenerate index/template files, and track every phase
mechanically. The rig deliberately does **not** do that: it would compete with
the orientation, symbol-lookup, and red-team capabilities the rig already has
(`repo-map`, serena/`memory`, `verification-council`) and resurrect the
template-generation pattern rejected in `derivation-not-templating.md`. The
durable, reusable part is this *policy* — when a human-curated doc earns an
update — not a generator. Keep the discipline; skip the machinery.

## See also

- `domains/project-journal/` — the working-notes discipline this policy governs.
- `domains/methodology/derivation-not-templating.md` — why we extract discipline,
  not parallel knowledge systems.
