#!/usr/bin/env bash
# sync-rig.sh [--dry-run] [--no-push] [--yes]
# The one blessed way to propagate rig changes to a running Claude Code.
#
# The rig has ONE source of truth (this git repo) and, unavoidably, TWO delivery
# paths:
#
#   plugin cache  <- skills, agents, hooks, MCP/LSP servers   (via the marketplace)
#   the checkout  <- Layer 1 (~/.claude/CLAUDE.md import) and the statusline
#
# The second path exists because Claude Code cannot deliver either through a
# plugin: "A CLAUDE.md file at the plugin root is not loaded as project
# context", and a plugin's settings.json honours only `agent` and
# `subagentStatusLine`. So the split is a constraint, not a design choice.
#
# The hazard is that the two paths serve DIFFERENT commits: Layer 1 reads the
# working tree and updates the instant you save, while hooks and skills stay on
# the last published commit. Prose rules then come from one version of the rig
# and the hooks enforcing them from another. This script closes that gap in one
# ordered pass, and `self-check`'s `delivery-paths-agree` reports when it is open.
set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARKET_DIR="${HOME}/.claude/plugins/marketplaces/claude-code-rig"
PLUGIN_ID="claude-code-rig@claude-code-rig"

DRY_RUN=0
NO_PUSH=0
ASSUME_YES=0
for arg in "$@"; do
    case "${arg}" in
        --dry-run) DRY_RUN=1 ;;
        --no-push) NO_PUSH=1 ;;
        --yes|-y)  ASSUME_YES=1 ;;
        -h|--help) sed -n '2,22p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "unknown option: ${arg}" >&2; exit 2 ;;
    esac
done

if [[ -t 1 ]]; then
    G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
else
    G=""; Y=""; R=""; N=""
fi
ok()   { printf '%s  OK %s  %s\n' "${G}" "${N}" "$1"; }
warn() { printf '%sWARN %s  %s\n' "${Y}" "${N}" "$1"; }
fail() { printf '%sFAIL %s  %s\n' "${R}" "${N}" "$1"; }
step() { printf '\n== %s ==\n' "$1"; }

confirm() {
    [[ "${ASSUME_YES}" -eq 1 ]] && return 0
    [[ ! -t 0 ]] && return 1
    local reply
    read -r -p "$1 [y/N] " reply
    [[ "${reply}" =~ ^[Yy]$ ]]
}

run_or_echo() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "    [dry-run] $*"
        return 0
    fi
    "$@"
}

# --- 1. the checkout must be committed -----------------------------------------
step "Checkout"
DIRTY="$(git -C "${RIG_DIR}" status --porcelain)"
if [[ -n "${DIRTY}" ]]; then
    fail "uncommitted changes — Layer 1 is already serving them while the plugin is not:"
    printf '%s\n' "${DIRTY}" | sed 's/^/       /'
    echo
    echo "Commit (or stash) first: the whole point of this script is to make both"
    echo "delivery paths serve the same commit."
    exit 1
fi
BRANCH="$(git -C "${RIG_DIR}" branch --show-current)"
HEAD_SHA="$(git -C "${RIG_DIR}" rev-parse --short HEAD)"
ok "clean, on '${BRANCH}' at ${HEAD_SHA}"

# --- 2. version gate ------------------------------------------------------------
# `claude plugin update` compares VERSION STRINGS, not commits: with plugin.json
# unchanged it answers "already at the latest version" and leaves the plugin on
# its old commit, however far the repo has moved. So any commit touching
# plugin-delivered content is undeliverable until the version bumps — which is
# how seven commits sat published-but-not-installed while everything looked fine.
step "Version"
PLUGIN_JSON="${RIG_DIR}/.claude-plugin/plugin.json"
CUR_VERSION="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "${PLUGIN_JSON}")"
LAST_BUMP="$(git -C "${RIG_DIR}" log -1 --format=%H -- "${PLUGIN_JSON}")"
# Paths the plugin actually ships (see .claude-plugin/plugin.json).
DELIVERED=(core domains skills .mcp.json .lsp.json .claude-plugin)
UNDELIVERED="$(git -C "${RIG_DIR}" log --oneline "${LAST_BUMP}..HEAD" -- "${DELIVERED[@]}" 2>/dev/null)"

if [[ -z "${UNDELIVERED}" ]]; then
    ok "v${CUR_VERSION} covers everything shipped"
else
    COUNT="$(printf '%s\n' "${UNDELIVERED}" | wc -l)"
    warn "${COUNT} commit(s) change shipped content since v${CUR_VERSION} was set:"
    printf '%s\n' "${UNDELIVERED}" | sed 's/^/       /'
    NEXT="$(python3 - "${CUR_VERSION}" <<'PY'
import sys
major, minor, patch = (sys.argv[1].lstrip("v").split(".") + ["0", "0"])[:3]
print(f"{major}.{minor}.{int(patch) + 1}")
PY
)"
    if confirm "Bump ${CUR_VERSION} -> ${NEXT} so the plugin can actually receive them?"; then
        if [[ "${DRY_RUN}" -eq 1 ]]; then
            echo "    [dry-run] bump to ${NEXT}, commit, tag v${NEXT}"
        else
            python3 - "${PLUGIN_JSON}" "${NEXT}" <<'PY'
import json, pathlib, re, sys
path, version = pathlib.Path(sys.argv[1]), sys.argv[2]
# Rewrite the value in place to preserve key order and formatting.
path.write_text(re.sub(r'("version":\s*")[^"]+(")', rf'\g<1>{version}\g<2>', path.read_text()))
PY
            printf 'v%s\n' "${NEXT}" > "${RIG_DIR}/VERSION"
            git -C "${RIG_DIR}" add "${PLUGIN_JSON}" "${RIG_DIR}/VERSION"
            git -C "${RIG_DIR}" commit -q -m "chore(release): v${NEXT}"
            git -C "${RIG_DIR}" tag -a "v${NEXT}" -m "v${NEXT}"
            HEAD_SHA="$(git -C "${RIG_DIR}" rev-parse --short HEAD)"
            ok "bumped to v${NEXT} (${HEAD_SHA}); remember a CHANGELOG entry"
        fi
    else
        warn "not bumped — the plugin will stay on v${CUR_VERSION} and ignore those commits"
    fi
fi

# --- 3. publish ----------------------------------------------------------------
step "Publish"
git -C "${RIG_DIR}" fetch --quiet origin 2>/dev/null || warn "fetch failed (offline?)"
AHEAD="$(git -C "${RIG_DIR}" rev-list --count "origin/${BRANCH}..HEAD" 2>/dev/null || echo 0)"
if [[ "${AHEAD}" -eq 0 ]]; then
    ok "origin/${BRANCH} already has ${HEAD_SHA}"
elif [[ "${NO_PUSH}" -eq 1 ]]; then
    warn "${AHEAD} commit(s) unpushed; --no-push set, so the plugin will not see them"
elif confirm "Push ${AHEAD} commit(s) to origin/${BRANCH}?"; then
    run_or_echo git -C "${RIG_DIR}" push origin "${BRANCH}" && ok "pushed"
else
    warn "not pushed; the plugin update below will not pick up local commits"
fi

# --- 4. the marketplace clone must be pristine ---------------------------------
# It is a real git checkout, so it can be hand-edited; those edits are invisible
# to the rig and are discarded by the update below. Surface them before that.
step "Marketplace clone"
if [[ -d "${MARKET_DIR}/.git" ]]; then
    SOILED="$(git -C "${MARKET_DIR}" status --porcelain)"
    if [[ -z "${SOILED}" ]]; then
        ok "pristine"
    else
        warn "hand-edited — these changes exist nowhere else and are about to be discarded:"
        printf '%s\n' "${SOILED}" | sed 's/^/       /'
        BACKUP="${HOME}/.claude/marketplace-local-edits-$(date +%Y%m%dT%H%M%S).patch"
        if [[ "${DRY_RUN}" -eq 0 ]]; then
            git -C "${MARKET_DIR}" diff > "${BACKUP}" && ok "backed up to ${BACKUP}"
        fi
        if confirm "Discard them and let the marketplace update proceed?"; then
            run_or_echo git -C "${MARKET_DIR}" checkout -- . && ok "reset"
        else
            fail "left as-is; the marketplace update will likely conflict"
            exit 1
        fi
    fi
else
    warn "no marketplace clone (plugin may be installed from a local path)"
fi

# --- 5. refresh both delivery paths --------------------------------------------
step "Deliver"
run_or_echo claude plugin marketplace update claude-code-rig || warn "marketplace update reported problems"
run_or_echo claude plugin update "${PLUGIN_ID}" || warn "plugin update reported problems"
# Layer 1 and the statusline need no step: they read the checkout directly.
ok "Layer 1 + statusline follow the checkout already (no action needed)"

# --- 6. prove it ---------------------------------------------------------------
step "Verify"
if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "    [dry-run] core/routines/run-routine.sh self-check"
    exit 0
fi
"${RIG_DIR}/core/routines/run-routine.sh" self-check >/dev/null 2>&1
VERDICT="${HOME}/.claude/data/self-check/latest.json"
if python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['ok'] else 1)" "${VERDICT}" 2>/dev/null; then
    ok "self-check passes — both delivery paths agree"
else
    fail "self-check reports problems:"
    python3 -c "
import json,sys
d = json.load(open(sys.argv[1]))
for name in d.get('failed', []):
    print('       -', name)
" "${VERDICT}" 2>/dev/null
    echo "       see ${HOME}/.claude/data/self-check/"
    exit 1
fi

echo
ok "rig synced at ${HEAD_SHA}. Restart Claude Code to pick up hooks and skills."
