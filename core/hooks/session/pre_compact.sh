#!/usr/bin/env bash
# PreCompact hook (matcher: auto|manual) — persist task state before a
# compaction can drop it.
#
# Rescoped from the GSD context-monitor idea: hook stdin carries no context
# budget (that field is statusline-only), so this acts on the guaranteed
# PreCompact event rather than a non-existent 35%/25% PostToolUse read. It backs
# up any tracked state file and reminds the session to run the save-state skill.
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

echo "=== PRE-COMPACT NOTICE ==="
if [ -n "${found}" ]; then
    echo "Context compaction imminent. Backed up task state to ${BACKUP_DIR}/ (${TIMESTAMP})."
    echo "Run the save-state skill now to capture anything not yet written, then"
    echo "re-read the backup + ~/.claude/learnings.md after compaction to restore context."
else
    echo "Context compaction imminent and no task-state file was found."
    echo "Run the save-state skill to snapshot the current objective before state is lost."
fi
echo "=========================="
