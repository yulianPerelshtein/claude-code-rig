#!/usr/bin/env bash
# Smoke test for the `scrapling` enhancement (Tier 2, opt-in, anti-bot escalation).
# Run AFTER a manual `pipx install "scrapling[ai]" && scrapling install`.
set -euo pipefail

if ! command -v scrapling >/dev/null 2>&1; then
    echo "scrapling: NOT installed. Install (deferred user action):" >&2
    echo '  pipx install "scrapling[ai]" && scrapling install' >&2
    echo "Default browser remains Playwright MCP; escalate to Scrapling only when" >&2
    echo "it demonstrably fails. See domains/scraping/scrapling.md." >&2
    exit 1
fi

echo "scrapling: OK ($(scrapling --version 2>/dev/null || echo unknown))"
echo "Reminder: do not install obscura alongside Scrapling (mutually exclusive)."
