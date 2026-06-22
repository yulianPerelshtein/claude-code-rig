#!/usr/bin/env bash
# Smoke test for the `claude-code-action` enhancement (Tier 2, opt-in, Claude-in-CI).
# The workflow ships with the rig; "installing" it means adding the API secret.
# This check confirms the workflow file is present and reminds about the secret +
# billing. Run from the repo root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
workflow="${REPO_ROOT}/.github/workflows/claude-code.yml"

if [[ ! -f "${workflow}" ]]; then
    echo "claude-code-action: workflow missing at .github/workflows/claude-code.yml" >&2
    exit 1
fi

echo "claude-code-action: workflow present (${workflow#"${REPO_ROOT}/"})"
echo "To enable: add the ANTHROPIC_API_KEY repo secret. It BILLS the API account."
echo "It is gated to workflow_dispatch + @claude mentions only (never on push)."
echo "See domains/observability/claude-code-action.md and playbooks/ci/claude-in-ci.md."
