#!/bin/bash
# SessionStart hook — prints lightweight session context.
#
# Context notes (skills-first):
#   - No full `cat` of learnings.md (token waste on every session start).
#     Distilled learnings load on demand (/load-learnings) or via
#     paths:-scoped domain skills.
#   - No domain glob-loader (domain activation is native `paths:` frontmatter).
echo "=== SESSION CONTEXT ==="
echo "Date: $(date '+%Y-%m-%d %H:%M')"
echo ""
echo "--- Git Status ---"
git -C "${CLAUDE_PROJECT_DIR:-.}" status --short 2>/dev/null || echo "(not a git repo)"
echo ""
echo "--- Recent Commits ---"
git -C "${CLAUDE_PROJECT_DIR:-.}" log --oneline -n 5 2>/dev/null || echo "(no commits)"
echo ""
echo "--- Active Branch ---"
git -C "${CLAUDE_PROJECT_DIR:-.}" branch --show-current 2>/dev/null || echo "(none)"
echo ""
echo "--- Running Containers ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "(docker not available)"
echo ""
echo "--- Learnings ---"
echo "Distilled learnings load on demand — run /load-learnings, or rely on"
echo "paths:-scoped domain skills that surface when you touch matching files."

# --- routines: first-session-today nudge for /begin-work ---
# A one-line nudge once per day (NOT an auto-run — auto-running the full startup
# routine on every session is noisy). The stamp lives in the routines run-state
# dir (mirrors the F.5 reminders pattern), never under ~/.claude.
NUDGE_STAMP="${HOME}/.local/share/cc-rig-routines/.last-begin-work-nudge"
mkdir -p "$(dirname "$NUDGE_STAMP")" 2>/dev/null
if [ "$(cat "$NUDGE_STAMP" 2>/dev/null)" != "$(date +%F)" ]; then
  echo ""
  echo "--- Routines ---"
  echo "Tip: first session today — run /begin-work for your startup brief."
  date +%F > "$NUDGE_STAMP" 2>/dev/null || true
fi
echo "=== END CONTEXT ==="
