#!/usr/bin/env bash
# rollback.sh — restore installer-managed files from the latest backup, using
# ~/.claude/.installed-from-rig.json as the manifest of truth.
set -uo pipefail
RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --with pyyaml python3 "${RIG_DIR}/install/lib/installer.py" rollback
