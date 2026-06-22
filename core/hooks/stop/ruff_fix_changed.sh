#!/bin/bash
# Stop hook — ruff --fix the Python files changed this session.
#
# Extracted from the inline settings.json Stop command
# (PACKAGE_STRUCTURE §3 / §17.7). ruff check --fix only: removes unused
# imports, fixes quote style, etc. Never runs `ruff format` (PR-noise).
[ -n "$CLAUDE_PROJECT_DIR" ] || exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0

files=$(
    git diff --name-only HEAD -- '*.py' 2>/dev/null
    git ls-files --others --exclude-standard -- '*.py' 2>/dev/null
)

[ -n "$files" ] && echo "$files" | xargs uv run ruff check --fix 2>/dev/null
exit 0
