#!/usr/bin/env bash
# install-extensions.sh [--upgrade]
# Clone the cc-extensions git packages at their pinned commits (per
# manifests/marketplace.yaml) and register the Claude Code marketplace.
# Idempotent: an existing clone is fetched + checked out to the pin; it is
# only advanced past the pin when --upgrade is given.
set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARKETPLACE="${RIG_DIR}/manifests/marketplace.yaml"
UPGRADE=0
[[ "${1:-}" == "--upgrade" ]] && UPGRADE=1

# Emit "id<TAB>source<TAB>pin<TAB>install_to<TAB>method" for each extension.
read_extensions() {
    uv run --with pyyaml python3 - "${MARKETPLACE}" <<'PY'
import sys, os, yaml
data = yaml.safe_load(open(sys.argv[1])) or {}
for e in data.get("extensions", []):
    print("\t".join([
        e.get("id", ""),
        e.get("source", ""),
        e.get("pinned_commit", ""),
        os.path.expanduser(e.get("install_to", "")),
        e.get("install_method", "git"),
    ]))
PY
}

while IFS=$'\t' read -r id source pin install_to method; do
    [[ -z "${id}" ]] && continue
    if [[ "${method}" == "claude_marketplace" ]]; then
        echo "[marketplace] ${id}: claude plugin marketplace add ${source}"
        command -v claude >/dev/null 2>&1 && claude plugin marketplace add "${source}" \
            || echo "  (skipped: claude CLI not available)"
        continue
    fi
    if [[ -d "${install_to}/.git" ]]; then
        echo "[fetch] ${id} (${install_to})"
        git -C "${install_to}" fetch --quiet origin || echo "  warn: fetch failed"
        if [[ "${UPGRADE}" -eq 1 ]]; then
            git -C "${install_to}" checkout --quiet "${pin}" && echo "  at pin ${pin:0:8}"
        else
            git -C "${install_to}" cat-file -e "${pin}^{commit}" 2>/dev/null \
                && echo "  pin ${pin:0:8} reachable (use --upgrade to advance)" \
                || echo "  warn: pin ${pin:0:8} not reachable"
        fi
    else
        echo "[clone] ${id} -> ${install_to}"
        mkdir -p "$(dirname "${install_to}")"
        git clone --quiet "${source}" "${install_to}" || { echo "  clone failed"; continue; }
        git -C "${install_to}" checkout --quiet "${pin}" && echo "  at pin ${pin:0:8}"
    fi
done < <(read_extensions)

echo "done."
