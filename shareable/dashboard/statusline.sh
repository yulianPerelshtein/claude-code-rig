#!/bin/bash
# statusline.sh — render the Claude Code status line.
#
# Reads the statusline JSON on stdin, pipes it through statusline_parse.py, and
# colourises the pipe-delimited result. Installed to ~/.claude/utils/ alongside
# statusline_parse.py (see install.sh).
INPUT=$(cat)

PARSED=$(echo "$INPUT" \
    | python3 ~/.claude/utils/statusline_parse.py 2>/dev/null \
    || echo "0|░░░░░░░░░░░░░░░░░░░░|0|0|0.00|||?||")

IFS='|' read -r USED BAR IN_TOK OUT_TOK COST SESSION_STR WEEKLY_STR MODEL_NAME AGENT_NAME WT_BRANCH \
    <<< "$PARSED"
USED=${USED:-0}

# ── Colors ────────────────────────────────────────────────────────────────────
if   [ "${USED}" -ge 80 ] 2>/dev/null; then CTX_C="\033[7;31m"
elif [ "${USED}" -ge 60 ] 2>/dev/null; then CTX_C="\033[7;33m"
else                                         CTX_C="\033[7;32m"
fi

# Rate limit color: extract leading number from "36% 1h5m"
_pct_color() {
    local pct
    pct=$(echo "$1" | grep -o '^[0-9]*')
    if   [ "${pct:-0}" -ge 90 ] 2>/dev/null; then echo "\033[1;31m"
    elif [ "${pct:-0}" -ge 75 ] 2>/dev/null; then echo "\033[33m"
    else                                           echo "\033[0m"
    fi
}

SESSION_C=$(_pct_color "$SESSION_STR")
WEEKLY_C=$(_pct_color "$WEEKLY_STR")

BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[36m"
MAG="\033[35m"
RESET="\033[0m"
SEP="  \033[2m│\033[0m  "

GIT_BRANCH=$(git -C "${CLAUDE_PROJECT_DIR:-.}" branch --show-current 2>/dev/null)

# ── Assemble ──────────────────────────────────────────────────────────────────
STATUS="${CTX_C} ${BAR} ${USED}% ${RESET}"
STATUS+="${SEP}${CYAN}↑${IN_TOK} ↓${OUT_TOK}${RESET}"
STATUS+="${SEP}${BOLD}\$${COST}${RESET}"
[ -n "$SESSION_STR" ] && STATUS+="${SEP}${SESSION_C}session ${SESSION_STR}${RESET}"
[ -n "$WEEKLY_STR"  ] && STATUS+="${SEP}${WEEKLY_C}weekly ${WEEKLY_STR}${RESET}"
[ -n "$GIT_BRANCH"  ] && STATUS+="${SEP}${BOLD}${MAG}⎇  ${GIT_BRANCH}${RESET}"
[ -n "$WT_BRANCH"   ] && STATUS+="${SEP}${CYAN}⎇  wt:${WT_BRANCH}${RESET}"
[ -n "$AGENT_NAME"  ] && STATUS+="${SEP}${CYAN}⚙ ${AGENT_NAME}${RESET}"
STATUS+="${SEP}${DIM}${MODEL_NAME}${RESET}"

echo -e "$STATUS"
