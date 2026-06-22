#!/usr/bin/env bash
# backup.sh [output.tgz]
# Tar ~/.claude into a timestamped archive, excluding high-volume / transient
# state (projects, file-history, todos, shell-snapshots, statsig) per
# SECURITY_REVIEW.md §6. Prints the archive path.
set -uo pipefail

CLAUDE_DIR="${HOME}/.claude"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-${HOME}/.claude.backup-${STAMP}.tgz}"

if [[ ! -d "${CLAUDE_DIR}" ]]; then
    echo "no ~/.claude directory to back up" >&2
    exit 1
fi

tar \
    --exclude='./projects' \
    --exclude='./file-history' \
    --exclude='./todos' \
    --exclude='./shell-snapshots' \
    --exclude='./statsig' \
    --exclude='./.credentials.json' \
    -czf "${OUT}" -C "${CLAUDE_DIR}" .

echo "backup written: ${OUT}"
