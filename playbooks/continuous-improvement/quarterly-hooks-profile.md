# Quarterly hooks profile

Hooks fire on every matching tool call, so a slow hook taxes the whole session
invisibly. Profile them quarterly and act on regressions.

## Cadence

Quarterly, ~15 minutes. Target: **p95 ≤ 30 ms** per hook.

## Procedure

1. **Run `/hooks-profile`** (or directly `bash tools/cli-helpers/cc-hooks-profiler.sh 20`
   in the rig repo). It feeds a benign sample payload to each `.py`/`.sh` hook
   under `core/hooks/` ~20 times and prints `hook | med(ms) | p95(ms)`,
   skipping `utils/` and `validators/` (libraries / CLI tools, not event hooks).
2. **Record the deltas.** Keep a short running table (date, slowest hook, its
   p95) so a regression is obvious quarter-over-quarter. A good home is a note
   alongside the dream reports, or a `## Hooks profile` section in your weekly
   review file.
3. **Fix any hook over 30 ms p95.** Common causes and fixes:
   - Spawning subprocesses on the hot path → inline the check in Python.
   - Re-compiling regexes per call → compile at module load.
   - Reading/rewriting a growing log every call → append JSONL instead
     (see `cost_tracker.py` / `post_tool_use_failure.py` for the pattern).
   - Doing work on the non-matching path → early-exit on the matcher first.
4. **Re-profile after a fix** to confirm the p95 came down.

## Why these hooks specifically

The injection scanner, guardrail, typecheck, and cost tracker run on most tool
calls; the dream loop and session-summary writer run at SessionEnd (off the hot
path, so latency there is far less critical). Focus the budget on the
PreToolUse/PostToolUse hooks.

## See also

- `core/skills/hooks-profile/SKILL.md` — the skill this playbook drives.
- `playbooks/continuous-improvement/weekly-retrospective.md` — the lighter
  weekly loop.
