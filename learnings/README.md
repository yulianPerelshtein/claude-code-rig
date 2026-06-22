# learnings/

Distilled, sanitized cross-project operational patterns.

## Files

- `distilled.md` — the canonical index of ~50 generic lessons, each a 1–3 line
  operational rule with `@`-references to the in-depth `domains/` / `playbooks/`
  doc. Format: `## YYYY-MM-DD CATEGORY-NAME`.

## Maintenance / drift policy

- One entry per distinct pattern; date when confirmed; ALL-CAPS-WITH-DASHES
  category. Keep entries to 1–3 lines (see `core/context-architecture.md`).
- `distilled.md` is **not** auto-loaded on session start. The session-start
  hook prints only a short cue; pull entries on demand (a `load-learnings`
  skill, or `@learnings/distilled.md`).
- Drift trigger: if the file grows past ~120 entries, compress (strip any
  verbose preambles) and promote repeated lessons into a domain/playbook doc,
  leaving only the one-liner here.
- Native `MEMORY.md` complements this file for per-repo, machine-local memory.

## Provenance

These entries are a sanitized superset of a personal `~/.claude/learnings.md`.
All company / product / vendor / project identifiers were removed during
distillation. Vendor-specific reverse-engineering entries were
dropped; domain-relevant geometry/USD/IFC lessons are maintained in a
separate private overlay rather than in this public rig.
