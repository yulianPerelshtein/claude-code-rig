# core/ — always-loaded minimal core

Everything here ships in **all** profiles and carries no company, project, or
vendor references. `CLAUDE.base.md` is Layer 1 (always loaded) and imports the
always-loaded knowledge files so each stays single-purpose and auditable.
`context-architecture.md` is on-demand reference (not imported) — pull it with
`@core/context-architecture.md` when editing the rig's structure.

## Knowledge files

| File | Purpose |
|---|---|
| `CLAUDE.base.md` | Layer-1 entry point; imports the rest. |
| `safety-rules.md` | Destructive-command, secret, and filesystem guardrails. |
| `default-workflows.md` | Task execution loop; TodoWrite; verification discipline. |
| `reasoning-preferences.md` | Tone + effort-aware calibration. |
| `context-architecture.md` | Layer/tier loading + precedence + drift monitor (on-demand reference, not always-loaded). |

## Executable core

- `skills/` — slash-command skills (commands ship as
  `disable-model-invocation` skills) plus the routine bodies.
- `agents/` — subagents (`code-reviewer`, `refactor`, `test-writer`,
  `pr-writer`, eval helpers).
- `styles/` — output styles. Just `production` (a maximum-terse mode switch);
  baseline tone lives always-on in `reasoning-preferences.md`, and interactive
  teaching is the `learning-mode` skill.
- `hooks/` — event hooks wired by the native `hooks.json` (PreToolUse
  guardrail, SessionStart/SessionEnd, the consolidation loop, …) plus shared
  `utils/`.
- `routines/` — the registry-driven routine runner and its templates.
- `validators/` — standalone plan/spec validators invoked by later skills.

## How to extend

- A rule belongs at the **highest layer where it is universally true**
  (`context-architecture.md`). Don't duplicate across layers.
- New universal rule → add to the appropriate core file (and import it from
  `CLAUDE.base.md` if it's a new file).
- Domain-specific knowledge → a `paths:`-scoped domain under `domains/`, not core.
