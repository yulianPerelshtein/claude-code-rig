#!/bin/bash
# Fires when a sub-agent launches. Injects global context so agents
# don't start blind — they already know your rules and past learnings.
echo "=== SUBAGENT CONTEXT INJECTION ==="
echo "You are a sub-agent. Read and follow ~/.claude/CLAUDE.md at all times."
echo ""
echo "--- Project Learnings ---"
cat ~/.claude/learnings.md 2>/dev/null || echo "(none yet)"
echo ""
if [ -f "${CLAUDE_PROJECT_DIR}/.claude/CLAUDE.md" ]; then
    echo "--- Project-Specific Rules ---"
    cat "${CLAUDE_PROJECT_DIR}/.claude/CLAUDE.md"
fi
echo "==================================="
