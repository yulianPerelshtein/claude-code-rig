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

# 1. CLAUDE.md — present AND its imports resolve. Layer 1 is normally a stub
# that `@`-imports the rig's core, so a bare existence check passes while
# loading nothing if the rig moved. Only line-leading @imports are checked;
# inline ones are rare here and would false-positive on e-mail addresses.
if [[ -s "${CLAUDE_DIR}/CLAUDE.md" ]]; then
    broken_import=""
    while IFS= read -r target; do
        [[ -e "${target/#\~/${HOME}}" ]] || broken_import="${target}"
    done < <(grep -oE '^@[^[:space:]]+' "${CLAUDE_DIR}/CLAUDE.md" | cut -c2-)
    [[ -z "${broken_import}" ]] \
        && ok "CLAUDE.md present (imports resolve)" \
        || fail "CLAUDE.md imports a missing file: ${broken_import}"
else
    fail "CLAUDE.md missing"
fi

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

# 6. dashboard statusline — resolve whatever settings.json points at. The old
# check hardcoded the bespoke install path, so it warned on a working plugin
# install that runs the statusline straight out of the rig.
sl_cmd="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("statusLine",{}).get("command",""))' \
    "${CLAUDE_DIR}/settings.json" 2>/dev/null)"
if [[ -z "${sl_cmd}" ]]; then
    warn "no statusLine configured in settings.json"
else
    sl_script="$(printf '%s' "${sl_cmd}" | grep -oE '[^[:space:]]*statusline[^[:space:]]*\.sh' | head -n1)"
    sl_script="${sl_script/#\~/${HOME}}"
    [[ -n "${sl_script}" && -x "${sl_script}" ]] \
        && ok "dashboard statusline present (${sl_script})" \
        || warn "statusLine configured but its script is missing or not executable: ${sl_script:-${sl_cmd}}"
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

# 10. cc-extensions clones. Read the expected set from marketplace.yaml rather
# than a hardcoded pair, which drifts silently as extensions are added, and name
# the missing ones so the warning is actionable. Grepped, not YAML-parsed, to
# keep this script dependency-free (python3 only).
MARKETPLACE_YAML="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/manifests/marketplace.yaml"
missing_ext=()
while IFS= read -r dest; do
    [[ -d "${dest/#\~/${HOME}}/.git" ]] || missing_ext+=("$(basename "${dest}")")
done < <(grep -oE '^\s+install_to:\s*~/cc-extensions/\S+' "${MARKETPLACE_YAML}" 2>/dev/null \
    | awk '{print $2}')
if [[ ${#missing_ext[@]} -eq 0 ]]; then
    ok "cc-extensions clones present"
else
    warn "cc-extensions not cloned: ${missing_ext[*]} (run install-extensions.sh)"
fi

echo
if [[ "${FAILED}" -eq 1 ]]; then
    echo "${R}validation FAILED${N}"
    exit 1
fi
echo "${G}validation passed${N}"
