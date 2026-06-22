#!/usr/bin/env bash
# bootstrap-wsl.sh — the normal entry-point for installing the rig.
#
# Does only what a plugin can't: verifies the WSL2 environment, ensures the
# secrets store exists, runs `claude doctor`, then installs the rig through the
# Claude Code marketplace (add this repo as a marketplace, install the plugin).
#
# The bespoke manifest installer (install/install-profile.sh) is a reserved
# fallback for a DLP-locked machine that cannot use the marketplace; it is NOT
# called here.
#
# Usage:
#   install/bootstrap-wsl.sh [--skip-plugin-install] [--yes] [-h|--help]
#
#   --skip-plugin-install  Run preflight + secrets only; do not touch Claude Code.
#   --yes                  Assume "yes" for optional install prompts.

set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_FILE="${HOME}/.local/etc/secrets.env"
MIN_CLAUDE_VERSION="2.1.80"

SKIP_PLUGIN_INSTALL=0
ASSUME_YES=0
CRITICAL_FAIL=0

if [[ -t 1 ]]; then
    C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
    C_GREEN=""; C_YELLOW=""; C_RED=""; C_RESET=""
fi

ok()   { printf '%s  OK %s  %s\n'   "${C_GREEN}"  "${C_RESET}" "$1"; }
warn() { printf '%sWARN %s  %s\n'   "${C_YELLOW}" "${C_RESET}" "$1"; }
fail() { printf '%sFAIL %s  %s\n'   "${C_RED}"    "${C_RESET}" "$1"; CRITICAL_FAIL=1; }

confirm() {
    # $1 = prompt. Returns 0 for yes.
    [[ "${ASSUME_YES}" -eq 1 ]] && return 0
    [[ ! -t 0 ]] && return 1
    local reply
    read -r -p "$1 [y/N] " reply
    [[ "${reply}" =~ ^[Yy]$ ]]
}

version_ge() {
    # $1 >= $2 ? using sort -V
    [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-plugin-install) SKIP_PLUGIN_INSTALL=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

echo "=== claude-code-rig bootstrap (rig: ${RIG_DIR}) ==="

# 1. WSL2
if [[ -e /proc/sys/fs/binfmt_misc/WSLInterop ]] || grep -qi microsoft /proc/version 2>/dev/null; then
    ok "WSL2 detected"
else
    warn "not detected as WSL2 (scripts assume Linux paths; continuing)"
fi

# 2. Ubuntu LTS
if command -v lsb_release >/dev/null 2>&1; then
    ok "distro: $(lsb_release -ds 2>/dev/null)"
else
    warn "lsb_release unavailable; cannot confirm Ubuntu LTS"
fi

# 3. systemd
if [[ -f /etc/wsl.conf ]] && grep -qE '^\s*systemd\s*=\s*true' /etc/wsl.conf; then
    ok "systemd enabled in /etc/wsl.conf"
else
    warn "systemd not confirmed in /etc/wsl.conf ([boot] systemd=true recommended)"
fi

# 4. git
if command -v git >/dev/null 2>&1 && version_ge "$(git --version | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1)" "2.40"; then
    ok "git $(git --version | grep -oE '[0-9]+\.[0-9.]+' | head -n1)"
else
    fail "git >= 2.40 required"
fi

# 5. gh
if command -v gh >/dev/null 2>&1; then
    ok "gh present ($(gh --version | head -n1))"
else
    warn "gh not found (recommended for PR workflows)"
fi

# 6. python3
if command -v python3 >/dev/null 2>&1 && version_ge "$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')" "3.10"; then
    ok "python3 $(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')"
else
    fail "python3 >= 3.10 required (3.12 recommended)"
fi

# 7. uv
if command -v uv >/dev/null 2>&1; then
    ok "uv present ($(uv --version))"
elif confirm "uv not found. Install via astral.sh installer?"; then
    curl -LsSf https://astral.sh/uv/install.sh | sh && ok "uv installed" || fail "uv install failed"
else
    fail "uv required (hooks run via 'uv run')"
fi

# 8. ruff  / 9. mypy
for tool in ruff mypy; do
    if command -v "${tool}" >/dev/null 2>&1 || uv tool list 2>/dev/null | grep -q "^${tool}\b"; then
        ok "${tool} available"
    elif command -v uv >/dev/null 2>&1 && confirm "${tool} not found. Install via 'uv tool install ${tool}'?"; then
        uv tool install "${tool}" && ok "${tool} installed" || warn "${tool} install failed"
    else
        warn "${tool} not available (recommended)"
    fi
done

# 10. node
if command -v node >/dev/null 2>&1; then
    ok "node present ($(node --version))"
else
    warn "node not found (Playwright MCP needs it; 'nvm install --lts')"
fi

# 11. claude
if command -v claude >/dev/null 2>&1; then
    CLAUDE_VER="$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"
    if [[ -n "${CLAUDE_VER}" ]] && version_ge "${CLAUDE_VER}" "${MIN_CLAUDE_VERSION}"; then
        ok "claude ${CLAUDE_VER}"
    else
        fail "claude >= ${MIN_CLAUDE_VERSION} required (found '${CLAUDE_VER:-none}'); upgrade Claude Code"
    fi
else
    fail "claude (Claude Code CLI) not found"
fi

# 12. notify-send
if command -v notify-send >/dev/null 2>&1; then
    ok "notify-send present"
else
    warn "notify-send not found (apt install libnotify-bin for desktop toasts)"
fi

# 13. ~/.local/bin on PATH
case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) ok "${HOME}/.local/bin on PATH" ;;
    *) warn "${HOME}/.local/bin not on PATH (add it for user-installed tools)" ;;
esac

# 14. secrets store
if [[ -f "${SECRETS_FILE}" ]]; then
    ok "secrets store exists (${SECRETS_FILE})"
else
    mkdir -p "$(dirname "${SECRETS_FILE}")"
    touch "${SECRETS_FILE}" && chmod 600 "${SECRETS_FILE}"
    ok "created empty secrets store ${SECRETS_FILE} (mode 600)"
fi
chmod 600 "${SECRETS_FILE}" 2>/dev/null || true

# 15. cc-extensions dir
if [[ -d "${HOME}/cc-extensions" ]]; then
    ok "${HOME}/cc-extensions exists"
else
    mkdir -p "${HOME}/cc-extensions" && ok "created ${HOME}/cc-extensions"
fi

echo
if [[ "${CRITICAL_FAIL}" -eq 1 ]]; then
    echo "${C_RED}Critical checks failed.${C_RESET} Resolve the FAIL items above, then re-run."
    exit 1
fi
ok "preflight passed"

if [[ "${SKIP_PLUGIN_INSTALL}" -eq 1 ]]; then
    echo "--skip-plugin-install set; stopping before Claude Code steps."
    exit 0
fi

echo
echo "=== Claude Code: doctor + marketplace install ==="
claude doctor || warn "'claude doctor' reported issues (review above)"

# Marketplace install (idempotent: add the repo as a single-plugin marketplace,
# then install the plugin from it).
if claude plugin marketplace add "${RIG_DIR}"; then
    ok "marketplace added"
else
    warn "marketplace add failed or already present"
fi
if claude plugin install "claude-code-rig@claude-code-rig"; then
    ok "plugin installed"
else
    fail "plugin install failed"
    exit 1
fi

echo
ok "bootstrap complete. Verify with: claude plugin list"
