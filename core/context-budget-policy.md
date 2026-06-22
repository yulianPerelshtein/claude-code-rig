# Context budget policy

Goal: keep the always-loaded core minimal, let everything else load only when
relevant, and lean on native context management rather than hand-built hooks.

## Tiered loading

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
it only when matching files are in play.

## Native context management (rely on this, don't rebuild it)

- **Auto-compaction** is native. On compaction, Claude Code re-attaches the
  most recent invocation of each skill (first ~5,000 tokens each, combined
  ~25,000-token budget, most-recent-first). Skill *descriptions* are not
  re-injected after compaction.
- **`/context`** shows live capacity; **`PreCompact`/`PostCompact`** hooks fire
  around a compaction. Proactive save-state belongs on `PreCompact` — hook
  stdin does NOT expose remaining context budget (only the statusline payload
  carries `context_window.*`). Do not build a PostToolUse "N% remaining" monitor.
- **`MEMORY.md`** is native, machine-local, zero-egress, and survives
  `/compact`. It is the cross-session memory backbone alongside `CLAUDE.md`.
- Prefer native token reduction first: prompt caching, context editing,
  compaction, and skills lazy-loading. Evaluate any third-party token-economy
  tool against these before adopting it.

## Learnings

- Distilled learnings are NOT auto-`cat`'d on session start. `session_start.sh`
  prints only a short cue; targeted entries come on demand (a `load-learnings`
  skill, or `@learnings/distilled.md`).
