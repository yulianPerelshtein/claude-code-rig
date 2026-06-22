#!/usr/bin/env bash
# cc-doctor.sh — quick environment + rig-install health report.
# Read-only; reports tool versions, auth, and where the rig is installed.
set -uo pipefail

if [[ -t 1 ]]; then G=$'\033[32m'; Y=$'\033[33m'; N=$'\033[0m'; else G=""; Y=""; N=""; fi
line() { printf '%-22s %s\n' "$1" "$2"; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "=== cc-doctor ==="
line "OS" "$(uname -srm)"
if grep -qi microsoft /proc/version 2>/dev/null; then line "WSL2" "${G}yes${N}"; else line "WSL2" "${Y}no${N}"; fi
for t in git gh python3 uv ruff node claude; do
    if have "$t"; then
        line "$t" "$("$t" --version 2>/dev/null | head -n1)"
    else
        line "$t" "${Y}not found${N}"
    fi
done

if have claude; then
    if claude auth status >/dev/null 2>&1; then line "claude auth" "${G}logged in${N}"; else line "claude auth" "${Y}not logged in${N}"; fi
    line "plugins" "$(claude plugin list 2>/dev/null | grep -c . || echo 0) listed"
fi

line "secrets store" "$([[ -f "${HOME}/.local/etc/secrets.env" ]] && echo present || echo missing)"
line "install record" "$([[ -f "${HOME}/.claude/.installed-from-rig.json" ]] && echo present || echo "none (plugin path?)")"
line "cc-extensions" "$(find "${HOME}/cc-extensions" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l) dir(s)"
echo "done."
