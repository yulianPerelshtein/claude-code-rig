# Generic hooks

Vendor-neutral Claude Code hooks. No company, project, or personal references.

| File | Event | Role |
|---|---|---|
| `guardrail.py` | PreToolUse | Blocks destructive commands (regex blocklist in `blocked-commands.json`) and reads/writes to the WSL Windows-drive mount. Exit 2 = blocked. |
| `blocked-commands.json` | — | The editable blocklist: `rm -rf`, force-push, hard reset, `chmod 777`, destructive SQL, credential reads, etc. |
| `post_tool_use_failure.py` | PostToolUseFailure | Logs failed tool calls (JSONL) and injects actionable guidance so Claude doesn't blindly retry. Self-contained. |
| `mcp_trimmer.py` | PostToolUse | Truncates MCP outputs over 15 KB to protect the context window. |
| `tests/` | — | `pytest` coverage: block/allow matrix + guidance routing. |

## Wire them up

Add to `~/.claude/settings.json` (adjust paths to where you copy the files):

```json
{
  "hooks": {
    "PreToolUse": [
      { "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/guardrail.py" }] }
    ],
    "PostToolUse": [
      { "matcher": "mcp__.*", "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/mcp_trimmer.py" }] }
    ],
    "PostToolUseFailure": [
      { "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/post_tool_use_failure.py" }] }
    ]
  }
}
```

`guardrail.py` loads `blocked-commands.json` from its own directory first, then
falls back to `~/.claude/hooks/blocked-commands.json` — keep the two files
together.

## Notes

- The Windows-mount block in `guardrail.py` is a WSL OS-isolation rule (it
  rejects any path under the Windows `C:` drive mount). If you do not run under
  WSL, delete the two mount-path `if` blocks in `guardrail.py`.
- `blocked-commands.json` is plain regex; edit freely. Patterns match
  case-insensitively within a single command segment.

## Test

```bash
python3 -m pytest tests/
```

MIT-licensed (see the bundle's top-level `LICENSE`).
