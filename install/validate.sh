#!/usr/bin/env bash
# validate.sh — post-install checks. Green checklist; exit 0 only if no FAIL.
# Adapted to the skills-first layout (skills/ rather than a commands/ tree).
set -uo pipefail

CLAUDE_DIR="${HOME}/.claude"
FAILED=0

if [[ -t 1 ]]; then
    G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
else
    G=""; Y=""; R=""; N=""
fi
ok()   { printf '%s  OK %s  %s\n' "${G}" "${N}" "$1"; }
warn() { printf '%sWARN %s  %s\n' "${Y}" "${N}" "$1"; }
fail() { printf '%sFAIL %s  %s\n' "${R}" "${N}" "$1"; FAILED=1; }

# 1. CLAUDE.md
[[ -s "${CLAUDE_DIR}/CLAUDE.md" ]] && ok "CLAUDE.md present" || fail "CLAUDE.md missing"

# 2. settings.json parses (if present)
if [[ -f "${CLAUDE_DIR}/settings.json" ]]; then
    python3 -c "import json,sys;json.load(open(sys.argv[1]))" "${CLAUDE_DIR}/settings.json" \
        && ok "settings.json parses" || fail "settings.json invalid JSON"
else
    warn "settings.json not present (plugin path merges settings natively)"
fi

# 3. hook scripts compile
hook_fail=0
if [[ -d "${CLAUDE_DIR}/hooks" ]]; then
    while IFS= read -r -d '' f; do
        case "${f}" in
            *.py) python3 -c 'import sys; compile(open(sys.argv[1]).read(), sys.argv[1], "exec")' "${f}" 2>/dev/null || { hook_fail=1; echo "  bad: ${f}"; } ;;
            *.sh) bash -n "${f}" 2>/dev/null || { hook_fail=1; echo "  bad: ${f}"; } ;;
        esac
    done < <(find "${CLAUDE_DIR}/hooks" -type f \( -name '*.py' -o -name '*.sh' \) -print0)
    [[ "${hook_fail}" -eq 0 ]] && ok "hook scripts compile" || fail "a hook failed to compile"
    # Copied hooks are NOT wired on the bespoke path: hooks.json is plugin-only
    # (every command uses ${CLAUDE_PLUGIN_ROOT}) and the installer doesn't splice
    # a settings.json "hooks" block. Make the gap loud, not silent.
    if ! python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("hooks") else 1)' "${CLAUDE_DIR}/settings.json" 2>/dev/null; then
        warn "hooks copied but NOT wired — bespoke hook execution is unimplemented (hooks.json runs via \${CLAUDE_PLUGIN_ROOT}, plugin-only); use the plugin/marketplace path for working hooks"
    fi
else
    warn "no ~/.claude/hooks (plugin path runs hooks from the plugin cache)"
fi

# 4. auth
if command -v claude >/dev/null 2>&1 && claude auth status >/dev/null 2>&1; then
    ok "claude auth OK"
elif [[ -f "${CLAUDE_DIR}/.credentials.json" ]]; then
    ok "credentials present"
else
    warn "not logged in (run: claude login)"
fi

# 5. claude version
if command -v claude >/dev/null 2>&1; then
    ok "claude $(claude --version 2>/dev/null | head -n1)"
else
    warn "claude CLI not found"
fi

# 6. dashboard statusline
if [[ -x "${CLAUDE_DIR}/utils/statusline.sh" ]]; then
    ok "dashboard statusline present"
else
    warn "dashboard statusline not installed"
fi

# 7/8. agents + skills frontmatter
fm_ok=1
check_frontmatter_dir() {
    local dir="$1"
    [[ -d "${dir}" ]] || return 0
    while IFS= read -r -d '' f; do
        head -n1 "${f}" | grep -q '^---' || { fm_ok=0; echo "  no frontmatter: ${f}"; }
    done < <(find "${dir}" -name '*.md' -path '*agents*' -print0 2>/dev/null)
}
check_frontmatter_dir "${CLAUDE_DIR}/agents"
while IFS= read -r -d '' f; do
    head -n1 "${f}" | grep -q '^---' || { fm_ok=0; echo "  no frontmatter: ${f}"; }
done < <(find "${CLAUDE_DIR}/skills" -name 'SKILL.md' -print0 2>/dev/null)
[[ "${fm_ok}" -eq 1 ]] && ok "agents + skills frontmatter parse" || warn "some frontmatter missing"

# 9. marketplace plugins
if command -v claude >/dev/null 2>&1 && claude plugin list >/dev/null 2>&1; then
    ok "marketplace plugins listable"
else
    warn "could not list marketplace plugins"
fi

# 10. cc-extensions clones
ext_ok=1
for ext in superpowers wshobson-agents; do
    [[ -d "${HOME}/cc-extensions/${ext}/.git" ]] || { ext_ok=0; }
done
[[ "${ext_ok}" -eq 1 ]] && ok "cc-extensions clones present" \
    || warn "some ~/cc-extensions clones missing (run install-extensions.sh)"

echo
if [[ "${FAILED}" -eq 1 ]]; then
    echo "${R}validation FAILED${N}"
    exit 1
fi
echo "${G}validation passed${N}"
