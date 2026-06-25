# Context Architecture — Canonical Reference

The rig's loading + precedence model. This is on-demand reference (not
always-loaded): pull it with `@core/context-architecture.md` when editing the
rig's structure. Two orthogonal axes — **where** a rule lives (layers) and
**when** content loads (tiers).

> Skills-first note (2026-06): upstream Claude Code merged commands into
> skills, so Layer 3 is now **skills** (a "command" is a skill with
> `disable-model-invocation: true`). Layer 7 is complemented by native
> `MEMORY.md`. The hierarchy is otherwise unchanged.

## Layer Hierarchy (where a rule lives + precedence)

```text
Layer 1: ~/.claude/CLAUDE.md          ← global, always loaded, universal rules only
Layer 2: <project>/.claude/CLAUDE.md  ← project-specific overrides and architecture
Layer 3: ~/.claude/skills/*/SKILL.md  ← skills (incl. commands = disable-model-invocation)
Layer 4: ~/.claude/agents/*.md        ← specialized subagents, invoked by name
Layer 5: ~/.claude/styles/*.md        ← output modes, invoked by /style
Layer 6: project memory files         ← persistent findings, loaded contextually
Layer 7: ~/.claude/learnings.md + native MEMORY.md  ← cross-project operational patterns
```

**Placement rule**: a rule belongs at the HIGHEST layer where it is universally
true. Never duplicate a rule across layers.

## Loading triggers (when content enters context)

Keep the always-loaded core minimal; let everything else load only when
relevant, and lean on native context management rather than hand-built hooks
(see `domains/context-engineering/native-context-levers.md`).

| Tier | What loads | When |
|---|---|---|
| 0 — Always | `CLAUDE.base.md` + its imported core files | Every session start |
| 1 — Domain | A domain's `SKILL.md` | Auto-activates when its `paths:` globs match files in context |
| 2 — Project | Project `CLAUDE.md` / `AGENTS.md` | When a session opens inside that project tree |
| 3 — Task | A specific `domains/<d>/<topic>.md`, a `playbooks/<area>/<name>.md`, or specific distilled-learning entries | On demand via `@filename` |
| 4 — Reference | `archive/`, deep references | Never auto-loaded |

**Domain activation is declarative via `paths:`** (skill frontmatter), not a
custom `session_start.sh` glob loader. Each domain ships a thin `SKILL.md`
whose `paths:` globs scope it to the relevant file types; Claude Code surfaces
it only when matching files are in play. Distilled learnings are likewise NOT
auto-`cat`'d at session start — `session_start.sh` prints only a short cue;
targeted entries come on demand (`/load-learnings`, or `@learnings/distilled.md`).

## Standard Project CLAUDE.md Template

```markdown
# <project-name>

<one-line description + distinct role vs other projects>

## Active Work  [omit if no active branch/plan]
Branch: `<branch>` — <status>. Plan: `<path>`

## Architecture
- `<file>` — <one-line role>
[list only non-obvious files]

## Style Overrides  [omit if identical to global]
- [only rules that DIFFER from global CLAUDE.md]

## Do Not
- [project-specific prohibitions only]
```

## learnings.md Entry Format

```markdown
## YYYY-MM-DD CATEGORY-NAME
[Operational rule — what/how only. No Context/Reason labels.]
```

- One entry per distinct pattern; date when confirmed; ALL-CAPS-WITH-DASHES category.
- 1–3 lines max; include exact commands, API paths, function names.

## Drift Monitor

Operationalized by the `/drift-check` skill (the duplication grep) and the
monthly `playbooks/continuous-improvement/monthly-drift-check.md` cadence.

**Triggers (check in order):**

1. `wc -l ~/.claude/learnings.md` — if >120: compress (strip verbose preambles).
2. `grep -rh "NEVER\|Do NOT\|must be" ~/.claude/CLAUDE.md <workspace>/*/.claude/CLAUDE.md 2>/dev/null | sort | uniq -d` — any phrase in 2+ files → remove from project layer.
3. New `settings.json` hook or skill added → audit Layer 1 for redundancy.
4. Before major branch handoff → verify project `CLAUDE.md` is current.

**Re-optimize (10 min):**

- learnings.md >120 lines → strip `**Context:**`/`**Reason:**` annotations.
- Duplicates found → keep in global, remove from project layer.
- Project CLAUDE.md >45 lines → push universal rules up to Layer 1.

> Native equivalents already cover what earlier drafts proposed as bespoke
> agents: the `InstructionsLoaded` hook
> (`domains/context-engineering/native-context-levers.md §5`) observes which
> instruction files actually load and why; `/drift-check` reports cross-layer
> duplicates. No Context-Validator / Session-Counter agent exists or is needed.
