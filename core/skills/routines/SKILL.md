---
name: routines
description: List, inspect, run, and enable/disable the rig's routines (named repeatable procedures bound to triggers).
argument-hint: "[list|status|run <name>|enable <name>|disable <name>]"
allowed-tools: Bash, Read
---

# /routines

Dispatcher for the rig's **routines** — named, repeatable procedures bound to
triggers (manual / scheduled / event) with an enforced outcome policy. Read the
registry and run-state, then act on the sub-command.

- **Registry:** `core/routines/registry.yaml` in the rig checkout, or
  `${CLAUDE_PLUGIN_ROOT}/core/routines/registry.yaml` when installed as a plugin.
- **Run-state + log:** `~/.local/share/cc-rig-routines/state.json` and `log.txt`.

## Sub-commands

- `list` (default): print a table of name, triggers, `target_default`, outcome,
  and enabled, read from the registry.
- `status`: per routine, show the last run date + status + artifact from
  `state.json` (or "never run" if absent).
- `run <name>`: invoke `core/routines/run-routine.sh <name> --target "$PWD"`.
  Add `--dry-run` if the user asks to preview without acting.
- `enable <name>` / `disable <name>`: run
  `systemctl --user enable --now cc-routine-<name>.timer` (or `disable --now`)
  and report the new timer state. Only routines with a `scheduled` trigger have a
  timer.

## Notes

- `dream-loop` is a **script-bodied** routine: it runs the shipped deterministic
  `core/hooks/session/dream_loop.py` directly (no LLM). Accepted candidates are
  promoted to a draft PR later by `/weekly-retro`; synthesis into learnings is
  the existing `/dream-report` skill.
- Routines never merge PRs and never push to a default branch; routines that
  mutate a repo do so only as draft PRs, and only the runner (not the model)
  enforces that.
