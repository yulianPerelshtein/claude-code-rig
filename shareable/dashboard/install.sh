#!/usr/bin/env bash
# install.sh — install the stdin-native statusline dashboard into ~/.claude/.
#
# Copies the statusline + cost-tracker + MCP-trimmer, splices the statusLine and
# hook entries into settings.json (preserving existing hooks), and seeds
# budget.json. Re-runnable; reverse with ./uninstall.sh.
#
# Honours CLAUDE_CONFIG_DIR if set, else uses ~/.claude.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
UTILS_DIR="${CLAUDE_DIR}/utils"
HOOKS_DIR="${CLAUDE_DIR}/hooks"
SETTINGS="${CLAUDE_DIR}/settings.json"
SNIPPET="${HERE}/settings.snippet.json"
TS="$(date +%Y%m%d-%H%M%S)"

green() { printf '  \033[32m✓\033[0m %s\n' "$1"; }

# 1. Claude Code present and >= 2.1.80 (rate_limits-on-stdin landed in 2.1.80).
if ! command -v claude >/dev/null 2>&1; then
    echo "error: Claude Code CLI ('claude') not found on PATH." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 not found on PATH." >&2
    exit 1
fi
VER="$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
if [ -n "${VER}" ] && ! python3 -c "import sys; v=tuple(int(x) for x in '${VER}'.split('.')); sys.exit(0 if v >= (2,1,80) else 1)"; then
    echo "error: Claude Code ${VER} is below the required 2.1.80." >&2
    exit 1
fi
green "Claude Code ${VER:-detected} (>= 2.1.80)"

# 2. Config root.
mkdir -p "${UTILS_DIR}" "${HOOKS_DIR}"
green "config root: ${CLAUDE_DIR}"

# 3. Back up anything we are about to overwrite.
for f in \
    "${UTILS_DIR}/statusline.sh" \
    "${UTILS_DIR}/statusline_parse.py" \
    "${HOOKS_DIR}/cost_tracker.py" \
    "${HOOKS_DIR}/mcp_trimmer.py" \
    "${SETTINGS}"; do
    if [ -e "${f}" ]; then
        cp -p "${f}" "${f}.bak-${TS}"
        green "backed up $(basename "${f}") -> $(basename "${f}").bak-${TS}"
    fi
done

# 4. Copy statusline files.
cp "${HERE}/statusline.sh" "${UTILS_DIR}/statusline.sh"
cp "${HERE}/statusline_parse.py" "${UTILS_DIR}/statusline_parse.py"
chmod +x "${UTILS_DIR}/statusline.sh"
green "installed statusline.sh + statusline_parse.py -> ${UTILS_DIR}/"

# 5. Copy hooks.
cp "${HERE}/hooks/cost_tracker.py" "${HOOKS_DIR}/cost_tracker.py"
cp "${HERE}/hooks/mcp_trimmer.py" "${HOOKS_DIR}/mcp_trimmer.py"
green "installed cost_tracker.py + mcp_trimmer.py -> ${HOOKS_DIR}/"

# 6. Splice statusLine + hook entries into settings.json (preserve existing).
python3 - "${SETTINGS}" "${SNIPPET}" <<'PY'
import json
import sys
from pathlib import Path

settings_path, snippet_path = sys.argv[1], sys.argv[2]
snippet = json.loads(Path(snippet_path).read_text())
try:
    settings = json.loads(Path(settings_path).read_text())
except Exception:
    settings = {}

settings["statusLine"] = snippet["statusLine"]

hooks = settings.setdefault("hooks", {})
for event, entries in snippet.get("hooks", {}).items():
    existing = hooks.setdefault(event, [])
    have = {h.get("command") for e in existing for h in e.get("hooks", [])}
    for entry in entries:
        cmds = [h.get("command") for h in entry.get("hooks", [])]
        if any(c in have for c in cmds):
            continue
        existing.append(entry)

Path(settings_path).write_text(json.dumps(settings, indent=2) + "\n")
PY
green "spliced statusLine + hooks into ${SETTINGS}"

# 7. Seed budget.json if absent (never overwrite real thresholds).
if [ ! -e "${CLAUDE_DIR}/budget.json" ]; then
    cp "${HERE}/budget.json.example" "${CLAUDE_DIR}/budget.json"
    green "seeded budget.json (edit weekly_usd / monthly_usd to taste)"
else
    green "budget.json already present (left untouched)"
fi

echo
echo "Done. Open a new Claude Code session to see the status line."
echo "Uninstall with: ${HERE}/uninstall.sh"
