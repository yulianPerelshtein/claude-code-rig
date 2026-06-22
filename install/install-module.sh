#!/usr/bin/env bash
# install-module.sh <module-id> [--dry-run] [--no-backup] [--force]
# Install a single module from manifests/install.manifest.yaml.
set -uo pipefail
RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -lt 1 ]]; then
    echo "usage: install-module.sh <module-id> [--dry-run] [--no-backup] [--force]" >&2
    exit 2
fi
module="$1"; shift
exec uv run --with pyyaml python3 "${RIG_DIR}/install/lib/installer.py" \
    apply --module "${module}" "$@"
