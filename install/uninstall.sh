#!/usr/bin/env bash
# uninstall.sh — remove installer-managed files (per the install record). Does
# not touch user files or ~/cc-extensions clones.
set -uo pipefail
RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --with pyyaml python3 "${RIG_DIR}/install/lib/installer.py" uninstall
