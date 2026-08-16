---
name: load-learnings
description: Load only the distilled-learnings entries for a given category, on demand
disable-model-invocation: true
argument-hint: "[category]"
---

Load a targeted subset of distilled learnings instead of the whole file (kept
out of the default context per `core/context-architecture.md`).

`$ARGUMENTS` is a category keyword (e.g. `ruff`, `aws`, `wsl`, `statusline`,
`tdd`, `git`). Steps:

1. Locate the learnings file. **`$CLAUDE_PLUGIN_ROOT` is exported only to plugin
   *hook* commands, not to Bash tool calls or skill bodies**, so resolve it
   rather than referencing it directly:

   ```bash
   for f in \
     "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/learnings/distilled.md" \
     $(ls -d "$HOME"/.claude/plugins/cache/*/claude-code-rig/*/ 2>/dev/null | sort -V | tail -n1)learnings/distilled.md \
     "learnings/distilled.md" \
     "$HOME/.claude/learnings/distilled.md"
   do
     [ -f "$f" ] && { printf 'using %s\n' "$f"; LEARNINGS="$f"; break; }
   done
   ```

   The last entry is the **bespoke-installer** path; it does not exist on a
   plugin install and was listed *first* here for months, so the primary lookup
   always missed. If none resolve, say so and stop — do not report "no matching
   entries", which reads as "no such learning" rather than "no file found".
2. If `$ARGUMENTS` is empty, list the available category headings only:
   `grep -E '^##' <file>` — then ask which to load.
3. Otherwise, print the entries whose `## YYYY-MM-DD CATEGORY` heading matches
   `$ARGUMENTS` (case-insensitive substring on the category), including each
   matched heading and the lines beneath it up to the next `##` heading. For
   example:

   ```bash
   awk -v pat="$ARGUMENTS" '
     /^## / { show = (tolower($0) ~ tolower(pat)) }
     show { print }
   ' <file>
   ```

4. If nothing matches, say so and show the available headings (step 2) so the
   user can pick a real category. Load only what matched — do not dump the whole
   file.
