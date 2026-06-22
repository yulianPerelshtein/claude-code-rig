#!/usr/bin/env bash
# uninstall.sh — remove the statusline dashboard from ~/.claude/.
#
# Removes the installed files, strips our statusLine + hook entries from
# settings.json (matched by command string), and leaves budget.json + your
# cost log alone (they are your data). Honours CLAUDE_CONFIG_DIR if set.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
UTILS_DIR="${CLAUDE_DIR}/utils"
HOOKS_DIR="${CLAUDE_DIR}/hooks"
SETTINGS="${CLAUDE_DIR}/settings.json"
SNIPPET="${HERE}/settings.snippet.json"

green() { printf '  \033[32m✓\033[0m %s\n' "$1"; }

# Remove installed files only when their content matches the shipped copy, so a
# user's own same-named hook (one this bundle never installed) is never deleted.
remove_if_ours() {
    local dst="$1" src="$2"
    [ -e "${dst}" ] || return 0
    if [ -f "${src}" ] && cmp -s "${src}" "${dst}"; then
        rm -f "${dst}"
        green "removed ${dst}"
    else
        printf '  - kept %s (differs from the bundled copy; not ours to remove)\n' "${dst}"
    fi
}

remove_if_ours "${UTILS_DIR}/statusline.sh"       "${HERE}/statusline.sh"
remove_if_ours "${UTILS_DIR}/statusline_parse.py" "${HERE}/statusline_parse.py"
remove_if_ours "${HOOKS_DIR}/cost_tracker.py"     "${HERE}/hooks/cost_tracker.py"
remove_if_ours "${HOOKS_DIR}/mcp_trimmer.py"      "${HERE}/hooks/mcp_trimmer.py"

# Strip our statusLine + hook entries from settings.json (by command string).
if [ -e "${SETTINGS}" ] && command -v python3 >/dev/null 2>&1; then
    python3 - "${SETTINGS}" "${SNIPPET}" <<'PY'
import json
import sys
from pathlib import Path

settings_path, snippet_path = sys.argv[1], sys.argv[2]
snippet = json.loads(Path(snippet_path).read_text())
try:
    settings = json.loads(Path(settings_path).read_text())
except Exception:
    sys.exit(0)

ours = {
    h.get("command")
    for entries in snippet.get("hooks", {}).values()
    for e in entries
    for h in e.get("hooks", [])
}

if settings.get("statusLine") == snippet.get("statusLine"):
    settings.pop("statusLine", None)

hooks = settings.get("hooks", {})
for event in list(hooks):
    kept = []
    for entry in hooks[event]:
        inner = [h for h in entry.get("hooks", []) if h.get("command") not in ours]
        if inner:
            entry["hooks"] = inner
            kept.append(entry)
    if kept:
        hooks[event] = kept
    else:
        hooks.pop(event, None)
if not hooks:
    settings.pop("hooks", None)

Path(settings_path).write_text(json.dumps(settings, indent=2) + "\n")
PY
    green "stripped statusLine + hooks from ${SETTINGS}"
fi

echo
echo "Done. budget.json and cost-log.jsonl were left in place (your data)."
echo "Statusline backups (statusline*.bak-*) under ${UTILS_DIR} were kept."
