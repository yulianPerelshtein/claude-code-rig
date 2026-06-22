#!/usr/bin/env bash
# export-shareable.sh --bundle <name> [--output <path>] [--dry-run]
#
# Build a sanitized, self-contained tarball from shareable/ only. Nothing from
# core/, domains/, playbooks/, learnings/, private/, or archive/ ever enters a
# bundle (SHARING_STRATEGY.md §1). All redaction + secret scans run before the
# tarball is produced; one hit aborts.
#
# Bundles:  dashboard | hooks | commands | playbooks | everything
#
# NOTE: the bundle source is the shareable/ subtree; a missing source is
# reported (the tool still runs, producing nothing).
set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="${RIG_DIR}/tools/scripts"
BUNDLE=""
OUTPUT=""
DRY_RUN=0

usage() { sed -n '2,12p' "${BASH_SOURCE[0]}"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bundle) BUNDLE="${2:-}"; shift 2 ;;
        --output) OUTPUT="${2:-}"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

[[ -z "${BUNDLE}" ]] && { echo "error: --bundle required" >&2; usage; exit 2; }

# Resolve bundle -> source subdirectories under shareable/.
declare -a SRC_DIRS
case "${BUNDLE}" in
    dashboard)  SRC_DIRS=("shareable/dashboard") ;;
    hooks)      SRC_DIRS=("shareable/generic-hooks") ;;
    commands)   SRC_DIRS=("shareable/generic-commands") ;;
    playbooks)  SRC_DIRS=("shareable/generic-playbooks") ;;
    everything) SRC_DIRS=("shareable/dashboard" "shareable/generic-hooks" \
                          "shareable/generic-commands" "shareable/generic-playbooks") ;;
    *) echo "unknown bundle: ${BUNDLE}" >&2; exit 2 ;;
esac

missing=0
for d in "${SRC_DIRS[@]}"; do
    [[ -d "${RIG_DIR}/${d}" ]] || { echo "missing source: ${d}"; missing=1; }
done
[[ "${missing}" -eq 1 ]] && { echo "nothing to export yet."; exit 1; }

STAGE="$(mktemp -d "/tmp/cc-rig-export-XXXXXX")"
trap 'rm -rf "${STAGE}"' EXIT

for d in "${SRC_DIRS[@]}"; do
    cp -r "${RIG_DIR}/${d}" "${STAGE}/"
done

echo "=== scans (any hit aborts) ==="
command -v gitleaks >/dev/null 2>&1 \
    && { gitleaks detect --source "${STAGE}" --no-git --redact || exit 1; } \
    || echo "  (gitleaks not installed; relying on local scans + CI)"
command -v trufflehog >/dev/null 2>&1 \
    && { trufflehog filesystem "${STAGE}" --no-update --fail || exit 1; } \
    || echo "  (trufflehog not installed; relying on local scans + CI)"
python3 "${SCRIPTS}/sanitize.py" "${STAGE}" || exit 1
python3 "${SCRIPTS}/verify-no-secrets.py" "${STAGE}" || exit 1

# Bundle metadata.
RIG_COMMIT="$(git -C "${RIG_DIR}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
cat > "${STAGE}/LICENSE" <<'LIC'
MIT License

Copyright (c) 2026 Yulian Perelshtein

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This MIT license applies to this shareable bundle only. The parent rig it was
exported from is all-rights-reserved.
LIC
cat > "${STAGE}/README.md" <<RDM
# claude-code-rig — shareable bundle (${BUNDLE})

Sanitized, self-contained subset of a personal Claude Code rig. MIT-licensed.
Built from rig commit ${RIG_COMMIT}. See INSTALL.md.
RDM
cat > "${STAGE}/INSTALL.md" <<RDM
# Install (${BUNDLE})

Copy the contents into your \`~/.claude/\` (back up first). See each
subdirectory's own notes for specifics.
RDM

STAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT="${OUTPUT:-${HOME}/exports/cc-${BUNDLE}-share-${RIG_COMMIT}-${STAMP}.tgz}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "dry-run: scans passed; would write ${OUTPUT}"
    exit 0
fi

mkdir -p "$(dirname "${OUTPUT}")"
tar --sort=name --owner=0 --group=0 --numeric-owner -czf "${OUTPUT}" -C "${STAGE}" .
echo "bundle written: ${OUTPUT}"
