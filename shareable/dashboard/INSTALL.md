# Install — statusline dashboard

## Requirements

- Claude Code **≥ 2.1.80** (the version that started passing `rate_limits` on
  the status-line stdin). Check with `claude --version`.
- `python3` on `PATH`.
- WSL, Linux, or macOS.

## Quick install

```bash
./install.sh
```

`install.sh` does exactly this, and is safe to re-run:

1. Verifies Claude Code ≥ 2.1.80 and `python3` are present.
2. Resolves your config root (`$CLAUDE_CONFIG_DIR`, else `~/.claude`).
3. Backs up any existing `utils/statusline.sh`, `utils/statusline_parse.py`,
   and `settings.json` (timestamped `.bak-<ts>` copies).
4. Copies `statusline.sh` + `statusline_parse.py` to `~/.claude/utils/`.
5. Copies `cost_tracker.py` + `mcp_trimmer.py` to `~/.claude/hooks/`.
6. Splices the `statusLine` and hook entries from `settings.snippet.json` into
   `~/.claude/settings.json`, **preserving your existing hooks**.
7. Seeds `~/.claude/budget.json` from `budget.json.example` only if absent.

Open a new Claude Code session to see the status line.

## Configure your budget

Edit `~/.claude/budget.json`:

```json
{ "weekly_usd": 25, "monthly_usd": 80 }
```

`cost_tracker.py` writes `~/.claude/budget-cache.json` with week/month spend on
each Stop event; surface it however you like.

## Custom config root

If your Claude config lives elsewhere:

```bash
CLAUDE_CONFIG_DIR=/path/to/.claude ./install.sh
```

## Uninstall

```bash
./uninstall.sh
```

Removes the four installed files and strips only the `statusLine` + hook
entries this bundle added (matched by command string). Your `budget.json`,
`cost-log.jsonl`, and the timestamped backups are left in place.
