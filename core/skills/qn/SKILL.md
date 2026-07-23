---
name: qn
description: Quick-note — append a timestamped line to today's Obsidian daily note
disable-model-invocation: true
---

Capture a quick note into today's daily journal.

Run the shared capture script. It resolves the vault from `$RIG_VAULT_DIR`
(default `~/notes`), scaffolds today's note from the vault's
`_templates/daily.md` when it is missing, appends a timestamped bullet under
`## Log`, and prints the note path:

```bash
rig="${CLAUDE_PLUGIN_ROOT:-${RIG_HOME:-$(ls -d "$HOME"/.claude/plugins/cache/*/claude-code-rig/*/ 2>/dev/null | sort -V | tail -1)}}"
bash "${rig%/}/tools/cli-helpers/qn.sh" "$ARGUMENTS"
```

`$CLAUDE_PLUGIN_ROOT` is only exported to hook commands, not to Bash tool calls,
hence the fallback: an explicit `$RIG_HOME`, then the newest installed plugin
cache directory.

Then confirm to the user the exact line captured and the file path it went to.
Do nothing else.
