# Forked investigation (`context: fork`)

Run a skill in a **forked subagent context** that doesn't pollute the main
conversation. The fork does the Read+Grep+Glob legwork and returns a *summary*;
the main thread stays lean.

Reference: `core/skill-frontmatter-reference.md` (the `context` + `agent` rows).

## The shape

```yaml
---
name: explore-area
description: Investigate a code area and report how it works
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---
Investigate the area named in $ARGUMENTS. Read the relevant files, trace the
data flow, and return a tight summary: entry points, key files (path:line),
the control/data flow, and any surprises. Do NOT modify files.
```

`context: fork` spawns a subagent whose transcript is **discarded** after it
returns — only its final summary re-enters the main conversation. `agent:`
points it at a purpose-built investigator (e.g. `Explore`).

## When it pays off

- Read-only investigation that would otherwise dump dozens of file reads and
  grep hits into the main context.
- Large-file or multi-file analysis where you only need the conclusion.
- Anything you'd mentally label "go figure out X and tell me the answer".

## When NOT to fork

- **Interactive** skills that need the live conversation turn-by-turn
  (e.g. `walkthrough` — the user says "next" between sections; a fork can't do
  that).
- Skills that **write** files as their primary job — the fork's edits and
  reasoning need to be visible/owned by the main thread (use the `refactor`
  agent's `isolation: worktree` for isolated writes instead).
- Tiny lookups where the fork's dispatch overhead outweighs the context saved.

## Forks vs. worktrees (don't confuse them)

- `context: fork` = **context isolation** for read-heavy investigation; returns
  a summary, writes nothing.
- `isolation: worktree` (see `core/agents/refactor.md`) = **filesystem
  isolation** for large writes; keeps the main working tree clean.

## Retrofit candidates in this rig

- `core/agents/code-reviewer.md` — read-only by definition (Read/Glob/Grep, no
  writes); a natural fork so a big review doesn't flood the main context.
- `core/skills/review-pr/SKILL.md` — its read-heavy reviewer agents (the ones
  that just Read+Grep and report) fork cleanly.
- Any future "summarize this subsystem" skill.

## See also

- `playbooks/ai-assisted-coding/parallel-agent-fan-out.md` — fan *multiple*
  forked investigators out in parallel.
- `playbooks/skill-techniques/dynamic-injection.md` — seed the fork with `!`
  injected context.
