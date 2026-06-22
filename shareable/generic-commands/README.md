# Generic commands (skills)

Vendor-neutral Claude Code skills. Each is a folder with a `SKILL.md` carrying
`disable-model-invocation: true`, so it runs only as an explicit slash command
(the folder name is the command, e.g. `/commit`).

| Skill | What `/<name>` does |
|---|---|
| `commit/` | Conventional commit with smart staging (skips lock/build files; never `--no-verify`). |
| `health/` | Environment health check (git, docker, toolchain versions, lint). |
| `save-state/` | Snapshot the current task to `~/.claude/session-state.md` before a compaction. |
| `walkthrough/` | Interactive, section-by-section code walkthrough for learning. |
| `wrap-up/` | Mine the session for reusable patterns and append them to `~/.claude/learnings.md`. |

## Install

Copy each folder into your skills directory:

```bash
cp -r commit health save-state walkthrough wrap-up ~/.claude/skills/
```

Then they're available as `/commit`, `/health`, `/save-state`, `/walkthrough`,
`/wrap-up`. (Plugin layouts: place them under your plugin's `skills/` instead.)

MIT-licensed (see the bundle's top-level `LICENSE`).
