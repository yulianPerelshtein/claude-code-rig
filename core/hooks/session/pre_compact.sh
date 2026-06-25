#!/usr/bin/env bash
# PreCompact hook (matcher: auto|manual) — persist task state before a
# compaction can drop it.
#
# Rescoped from the GSD context-monitor idea: hook stdin carries no context
# budget (that field is statusline-only), so this acts on the guaranteed
# PreCompact event rather than a non-existent 35%/25% PostToolUse read. It backs
# up any tracked state file before compaction can drop it.
#
# PreCompact stdout goes to the debug log only and PreCompact supports no
# additionalContext channel, so this hook does NOT try to nudge the model — it
# performs the backup side effect and logs one honest line. (A genuine
# post-compaction nudge would belong on SessionStart matcher=compact.)
set -uo pipefail

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="${HOME}/.claude/compact-backups"
mkdir -p "${BACKUP_DIR}"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${PWD}}"
STATE_FILES=(
    "${PROJECT_DIR}/.planning/STATE.md"
    "${HOME}/.claude/session-state.md"
)

found=""
for f in "${STATE_FILES[@]}"; do
    if [ -f "${f}" ]; then
        if cp "${f}" "${BACKUP_DIR}/$(basename "${f}" .md)_${TIMESTAMP}.md" 2>/dev/null; then
            found="${f}"
        fi
    fi
done

# Debug-log only (PreCompact stdout is not shown to the model) — one honest line.
if [ -n "${found}" ]; then
    echo "pre-compact: backed up ${found} to ${BACKUP_DIR}/ (${TIMESTAMP})"
else
    echo "pre-compact: no task-state file found to back up"
fi
