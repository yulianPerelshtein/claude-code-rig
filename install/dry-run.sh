#!/usr/bin/env bash
# dry-run.sh <profile> — preview a profile install (no writes). Wraps
# install-profile.sh --dry-run.
set -uo pipefail
RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -lt 1 ]]; then
    echo "usage: dry-run.sh <profile>" >&2
    exit 2
fi
exec "${RIG_DIR}/install/install-profile.sh" "$1" --dry-run
