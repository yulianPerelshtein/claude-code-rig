# Claude Code statusline dashboard

A clean, self-contained status line for Claude Code on WSL / Linux / macOS.
Shows context-window usage, token counts, session cost, and your 5-hour /
7-day rate-limit windows — all rendered from the JSON Claude Code already
passes to the status line on stdin. **No API calls, no auth, no network, no
credential files.**

```text
 ████████░░░░░░░░░░░░ 42%  │  ↑113k ↓0  │  $0.83  │  session 36%  │  weekly 15%  │  ⎇  main  │  sonnet
```

## What's in here

| File | Role |
|---|---|
| `statusline.sh` | Renders + colourises the line (installed to `~/.claude/utils/`). |
| `statusline_parse.py` | Parses the stdin JSON into a pipe-delimited line. Reads `rate_limits` straight from stdin. |
| `hooks/cost_tracker.py` | Stop hook: aggregates per-week / per-month spend into `budget-cache.json`. |
| `hooks/mcp_trimmer.py` | PostToolUse hook: trims oversized MCP outputs (>15 KB). |
| `budget.json.example` | Copy to `~/.claude/budget.json`; set your weekly/monthly USD limits. |
| `settings.snippet.json` | The `statusLine` + hook entries `install.sh` splices into `settings.json`. |
| `install.sh` / `uninstall.sh` | One-command install / clean removal. |
| `tests/` | `pytest` coverage for the parser, with stdin fixtures. |

## Rate limits

Claude Code v2.1.80+ passes
`rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}` (epoch seconds)
on the status-line stdin for Claude.ai Pro / Max / Team sessions. The parser
reads those fields directly. On Bedrock / Vertex / Foundry the fields are
absent and the session/weekly segments render empty — which is correct there.

## Install

Requires Claude Code ≥ 2.1.80 and `python3`. See [`INSTALL.md`](./INSTALL.md).

```bash
./install.sh
```

Reverse with `./uninstall.sh`. Existing `statusline*` files and `settings.json`
are backed up first; your `budget.json` and cost log are never overwritten.

## License

MIT — see [`LICENSE`](./LICENSE). This bundle is independent of any parent
project it may have been exported from.
