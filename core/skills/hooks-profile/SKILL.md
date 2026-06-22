---
name: hooks-profile
description: Measure per-hook latency to catch slow hooks before they tax every tool call
disable-model-invocation: true
---

Profile the latency of the rig's hooks and report median + p95 per hook, so a
slow hook (which fires on every tool call) is caught early. Target: p95 ≤ 30 ms.

Steps:

1. Run the profiler helper if present:
   - In the rig repo: `bash tools/cli-helpers/cc-hooks-profiler.sh 20`
   - It feeds a benign sample payload to each `.py`/`.sh` hook under
     `core/hooks/` 20 times and prints `hook | med(ms) | p95(ms)` (skipping
     `utils/` and `validators/`, which are libraries / CLI tools, not event
     hooks).
2. If the helper is not available (e.g. on an installed machine where only
   `~/.claude/hooks/` exists), time each hook directly: for each `*.py`/`*.sh`
   under `~/.claude/hooks/`, pipe
   `{"tool_name":"Bash","tool_input":{"command":"ls"},"session_id":"profile"}`
   into it ~20 times and compute median + p95 from the elapsed times.
3. Flag any hook whose p95 exceeds 30 ms and suggest a fix (e.g. avoid spawning
   subprocesses, cache compiled regexes, early-exit on the non-matching path).
4. Report a short table and the single slowest hook. Run quarterly.
