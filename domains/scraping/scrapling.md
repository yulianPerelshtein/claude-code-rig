# Scrapling (anti-bot scraping escalation) — Tier 2, opt-in

[Scrapling](https://github.com/D4Vinci/Scrapling) is an adaptive Python
web-scraping framework with three fetchers (HTTP/3, stealth Playwright, full
Playwright) and an MCP server (`scrapling[ai]`). BSD-3, ~64k★, mature (92% test
coverage). It is the rig's **anti-bot escalation** above the default Playwright
MCP — opt-in only (`profiles/enhanced-tier2.yaml`).

## Where it sits in the scraping ladder

1. **Default:** Playwright MCP (`domains/scraping/playwright-mcp.md`) — official,
   deterministic, accessibility-tree driven. Use it for normal browser work.
2. **Escalation (this doc):** Scrapling — when a target actively blocks
   automation (bot detection, fingerprinting) and Playwright MCP can't get the
   page. Its stealth fetcher + adaptive selectors survive markup churn better.
3. **Watch-list:** obscura stays watch-list only (v0.1.x, partial CDP).

Reach for Scrapling only when the default demonstrably fails — don't make it the
first tool.

## Mutual exclusion with obscura

The rig's installer **refuses to install Scrapling and obscura simultaneously**.
`enhanced-tier2.yaml` declares one or the other, never both — enforced by
`conflicts_with` in `manifests/marketplace.yaml#enhancements` (the installer
exits with the conflicting pair if both appear). Default escalation = Scrapling;
obscura is not packaged.

## Install (deferred user action)

```bash
pipx install "scrapling[ai]"     # isolated env, not bare pip
scrapling install                # fetch the browser deps it needs
```

Then run its MCP server, or use it directly from a scraping script. The
`enhancements/scrapling/smoke-test.sh` verifies the CLI resolves after a manual
install.

## See also

- `domains/scraping/playwright-mcp.md` — the default driver (try first).
- `domains/scraping/SKILL.md` — the scraping ladder overview.
- `profiles/enhanced-tier2.yaml` — the opt-in profile.
