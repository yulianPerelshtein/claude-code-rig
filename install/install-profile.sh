#!/usr/bin/env bash
# install-profile.sh <profile> [--dry-run] [--no-backup] [--force]
# Bespoke fallback installer: copies the profile's files into ~/.claude with
# backups and an install record. Normal installs use bootstrap-wsl.sh (plugin).
set -uo pipefail
RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -lt 1 ]]; then
    echo "usage: install-profile.sh <profile> [--dry-run] [--no-backup] [--force]" >&2
    exit 2
fi
exec uv run --with pyyaml python3 "${RIG_DIR}/install/lib/installer.py" apply "$@"
