# Context Architecture — Canonical Reference

> Skills-first note (2026-06): upstream Claude Code merged commands into
> skills, so Layer 3 is now **skills** (a "command" is a skill with
> `disable-model-invocation: true`). Layer 7 is complemented by native
> `MEMORY.md`. The hierarchy is otherwise unchanged.

## Layer Hierarchy

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

**Triggers (check in order):**

1. `wc -l ~/.claude/learnings.md` — if >120: compress (strip verbose preambles).
2. `grep -rh "NEVER\|Do NOT\|must be" ~/.claude/CLAUDE.md <workspace>/*/.claude/CLAUDE.md 2>/dev/null | sort | uniq -d` — any phrase in 2+ files → remove from project layer.
3. New `settings.json` hook or skill added → audit Layer 1 for redundancy.
4. Every 20 sessions in a repo → run the `health` skill.
5. Before major branch handoff → verify project `CLAUDE.md` is current.

**Re-optimize (10 min):**

- learnings.md >120 lines → strip `**Context:**`/`**Reason:**` annotations.
- Duplicates found → keep in global, remove from project layer.
- Project CLAUDE.md >45 lines → push universal rules up to Layer 1.

## Recommended Agents

- **Context Validator** — PostToolUse on CLAUDE.md write: check no cross-layer
  duplicates, learnings.md size, project-template compliance.
- **Stale Entry Pruner** — quarterly: archive resolved dead ends to project memory.
- **Session Counter** — `session_start.sh`: per-project count; emit "Drift check
  due — run health" at 20.
