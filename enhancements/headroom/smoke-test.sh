#!/usr/bin/env bash
# Smoke test for the `headroom` enhancement (Tier 2, opt-in).
# Run AFTER a manual `pipx install "headroom-ai[all]"`. Exits 0 if headroom is
# installed and reachable; non-zero with guidance otherwise.
set -euo pipefail

if ! command -v headroom >/dev/null 2>&1; then
    echo "headroom: NOT installed. Install (deferred user action):" >&2
    echo '  pipx install "headroom-ai[all]"' >&2
    echo "See domains/context-engineering/headroom.md for the caveats first." >&2
    exit 1
fi

version="$(headroom --version 2>/dev/null || echo unknown)"
echo "headroom: OK (${version})"
echo "Reminder: verify no phone-home and leave 'headroom learn' disabled."
