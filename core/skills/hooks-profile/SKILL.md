---
name: hooks-profile
description: Measure per-hook latency to catch slow hooks before they tax every tool call
disable-model-invocation: true
---

Profile the latency of the rig's hooks and report median + p95 per hook, so a
slow hook (which fires on every tool call) is caught early. Target: p95 ≤ 30 ms.

Steps:

1. Resolve the rig root, then run the profiler helper. **`$CLAUDE_PLUGIN_ROOT`
   is exported only to plugin *hook* commands — it is NOT set in Bash tool calls
   or skill bodies**, so it needs a fallback chain rather than direct use. The
   cache path is nested by marketplace, plugin and version, not flat:

   ```bash
   rig_root() {
     [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && { printf '%s\n' "${CLAUDE_PLUGIN_ROOT%/}"; return; }
     local newest
     newest=$(ls -d "$HOME"/.claude/plugins/cache/*/claude-code-rig/*/ 2>/dev/null | sort -V | tail -n1)
     [ -n "${newest}" ] && { printf '%s\n' "${newest%/}"; return; }
     git rev-parse --show-toplevel 2>/dev/null   # running inside the rig checkout
   }
   RIG=$(rig_root)
   bash "${RIG}/tools/cli-helpers/cc-hooks-profiler.sh" 20
   ```

   It feeds a benign sample payload to each `.py`/`.sh` hook under `core/hooks/`
   20 times and prints `hook | med(ms) | p95(ms)` (skipping `utils/` and
   `validators/`, which are libraries / CLI tools, not event hooks).
2. If the helper cannot be found, time the hooks directly — **against
   `${RIG}/core/hooks/`, which is where they actually run from.**
   Do not target `~/.claude/hooks/`: that path belongs to the bespoke installer
   and does not exist on a plugin install, so this fallback profiled an empty
   directory and reported nothing to fix. For each `*.py`/`*.sh` there, pipe
   `{"tool_name":"Bash","tool_input":{"command":"ls"},"session_id":"profile"}`
   into it ~20 times and compute median + p95 from the elapsed times.
3. Flag any hook whose p95 exceeds 30 ms and suggest a fix (e.g. avoid spawning
   subprocesses, cache compiled regexes, early-exit on the non-matching path).
4. Report a short table and the single slowest hook. Run quarterly.
