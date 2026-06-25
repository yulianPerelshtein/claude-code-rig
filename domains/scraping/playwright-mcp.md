# Playwright MCP

The official Microsoft Playwright MCP server is the rig's **default** browser
driver for agents (locked, `SOTA_REFRESH.md §4.2`): official, mature, and
deterministic. It drives the browser through the **accessibility tree**, not
pixels/screenshots, so actions are structured and reproducible rather than
vision-guessed.

> Install-deferred user action. The server is already declared in `.mcp.json`;
> it lights up once `npx`/Node and the browser are present on the machine.

## Declared in `.mcp.json`

```json
"playwright": {
  "command": "npx",
  "args": ["-y", "@playwright/mcp@latest"]
}
```

`npx -y` fetches the package on first use. The first run may also need a browser
binary — install it with `npx playwright install chromium` if the server reports
a missing browser.

## What you get

- Accessibility-tree navigation, clicks, typing, form fill, and waits driven by
  structured snapshots — deterministic, no screenshot-pixel guessing.
- Console/network inspection and page content extraction for scraping rendered
  (JS-heavy) pages that a plain fetch can't see.

## When to use it

- A task needs a **real browser**: a JS-rendered page, an authenticated UI flow,
  a multi-step web interaction.
- Scraping content that only exists after client-side rendering.

For static pages, a plain HTTP fetch is cheaper — don't spin up a browser for
HTML you can `curl`.

## Keep its tool surface cheap

Playwright MCP exposes many tools. Two native levers keep that from inflating
context:

- MCP tool *schemas* are deferred by default (only tool names enter context
  until a tool is first used) via `ENABLE_TOOL_SEARCH`; it is on unless set to
  `false`, and the rig pins `"true"` in the settings template. This is the native
  #27 lever — see `domains/context-engineering/native-context-levers.md` for the
  value table (`auto` is threshold mode, not "always defer").
- The `mcp_trimmer.py` PostToolUse hook (already wired in `hooks.json`) trims
  oversized MCP tool responses so a large page snapshot doesn't flood context.

See `domains/context-engineering/native-context-levers.md` for the rig's native-context-first stance.

## Escalation (not default)

If a target actively blocks automation (bot detection, fingerprinting),
escalate to **Scrapling** (Tier 2, opt-in — `ENHANCEMENTS_BACKLOG.md §3.3`).
**obscura** remains watch-list only (v0.1.x, partial CDP). Don't reach for these
unless Playwright MCP demonstrably fails on the page.

## See also

- `.mcp.json` — the server declaration.
- `domains/context-engineering/native-context-levers.md` — native-context-first stance.
- `domains/context-engineering/native-context-levers.md` — `ENABLE_TOOL_SEARCH` value table + the other #27 levers.
- `core/hooks/post-tool/mcp_trimmer.py` — trims oversized MCP tool output.
