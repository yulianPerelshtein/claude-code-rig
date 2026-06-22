#!/usr/bin/env bash
# Smoke test for the `ai-engineering-coach` enhancement (Tier 2, opt-in).
# There is NO prebuilt VSIX — it must be built from source and installed into
# VS Code. Run AFTER that manual build. Best-effort: checks the VS Code CLI for
# an installed coach extension.
set -euo pipefail

if ! command -v code >/dev/null 2>&1; then
    echo "ai-engineering-coach: VS Code CLI ('code') not found on PATH." >&2
    echo "Build the VSIX from source (no prebuilt release) and install it; see" >&2
    echo "domains/observability/ai-engineering-coach.md." >&2
    exit 1
fi

if code --list-extensions 2>/dev/null | grep -qi 'coach'; then
    echo "ai-engineering-coach: OK (extension present in VS Code)"
    echo "Reminder: confirm it parses Claude Code sessions on WSL2."
    exit 0
fi

echo "ai-engineering-coach: VS Code found but the coach extension is not installed." >&2
echo "Build from source (Dev Container or local Node + vsce package) then install." >&2
exit 1
