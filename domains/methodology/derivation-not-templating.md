# Derivation, not templating

Pattern-borrowed from arscontexta (a Claude Code plugin that generates a personal
knowledge system from a ~20-min conversation; MIT, ~3.4k★, but stale — ~10
commits, no tags). We adopt the **thesis**, not the plugin — generating a parallel
knowledge system would compete with the one this rig already curates. See
`ENHANCEMENTS_BACKLOG.md §4.4` (#21, Tier 3, docs-only).

## The thesis

> **Derive, don't template.** Every structural choice in a personal knowledge
> system should be traceable to *evidence about how you actually work* — copying
> someone else's template produces an ill-fitting system you don't maintain.

This is the principle behind why this rig was *distilled from the user's real
`~/.claude` history* rather than cloned from a starter kit. When
adding to the rig, prefer the same: a new domain/playbook/skill should answer a
demonstrated, recurring need (a repeated prompt, a real lesson), not a "best
practices" checklist someone published.

## Reusable artifacts (the parts worth keeping)

- **The 6 Rs of a knowledge loop:** Record → Reduce → Reflect → Reweave →
  Verify → Rethink. The rig already implements this: capture (`/wrap-up`,
  session summaries) → reduce (dream-loop theme aggregation, learnings
  compaction) → reflect (`/dream-report`) → reweave (route into
  `learnings/distilled.md` / new skills) → verify (verification council,
  drift-check) → rethink (monthly drift check). Use the 6 Rs as a checklist that
  the loop has no missing stage.
- **Fresh context per phase via subagent spawning:** do bounded work in a forked
  subagent and return only the result — keeps the main context clean. The rig's
  `context: fork` (`playbooks/skill-techniques/forked-investigation.md`) is
  exactly this.
- **A `kernel.yaml` of primitives:** arscontexta defines ~15 primitives every
  personal system needs. The idea worth borrowing: keep an explicit, small set of
  *non-negotiable* primitives (for this rig: safety rules, redaction policy,
  context-architecture precedence, the improvement loop) and derive everything
  else around them — don't let the rig sprawl into un-anchored features.

## What we do NOT adopt

The arscontexta plugin itself (don't add to `manifests/marketplace.yaml` — no
releases/tags yet) and its generated-system approach (switch cost > gains given
the rig is already curated). Thesis only.

## See also

- `playbooks/continuous-improvement/` — the rig's Record→Rethink loop in practice.
- `domains/methodology/progressive-skill-activation.md` — the sibling activation lesson.
- `core/context-architecture.md` — the rig's anchored primitives + precedence.
