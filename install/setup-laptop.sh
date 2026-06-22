#!/usr/bin/env bash
# setup-laptop.sh — one-time prerequisite setup for a fresh WSL2 Ubuntu, run
# once before the rig's bootstrap. Installs base apt packages, Python, Node (via
# nvm), uv + ruff + mypy, and Claude Code; enables systemd; ensures ~/.local/bin
# on PATH and the secrets store. Idempotent: re-running skips what is present.
#
# Order on a fresh laptop:
#   1. (Windows PowerShell)  wsl --install -d Ubuntu-24.04   + reboot + create user
#   2. (Ubuntu)  sudo apt update && sudo apt install -y git gh
#   3. (Ubuntu)  gh auth login         # GitHub account (the repo is public)
#   4. (Ubuntu)  gh repo clone yulianPerelshtein/claude-code-rig ~/claude-code-rig
#   5. (Ubuntu)  ~/claude-code-rig/install/setup-laptop.sh
#   6. (Ubuntu)  claude auth login      # the Claude.ai account (Team/Pro/Max)
#   7. (Ubuntu)  ~/claude-code-rig/install/bootstrap-wsl.sh   # marketplace install
#
# Usage: install/setup-laptop.sh [--yes]
#   --yes   assume yes for apt + tool install prompts (still needs sudo password).
set -uo pipefail

ASSUME_YES=0
[[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]] && ASSUME_YES=1
MIN_CLAUDE_VERSION="2.1.80"

if [[ -t 1 ]]; then
    C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
    C_GREEN=""; C_YELLOW=""; C_BOLD=""; C_RESET=""
fi
ok()   { printf '%s  OK %s  %s\n'   "${C_GREEN}"  "${C_RESET}" "$1"; }
warn() { printf '%sWARN %s  %s\n'   "${C_YELLOW}" "${C_RESET}" "$1"; }
step() { printf '\n%s== %s ==%s\n'  "${C_BOLD}"   "$1" "${C_RESET}"; }

confirm() {
    [[ "${ASSUME_YES}" -eq 1 ]] && return 0
    [[ ! -t 0 ]] && return 0
    local reply
    read -r -p "$1 [Y/n] " reply
    [[ -z "${reply}" || "${reply}" =~ ^[Yy]$ ]]
}

version_ge() { [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]; }

# --- 0. sanity ---------------------------------------------------------------
step "Environment"
if grep -qi microsoft /proc/version 2>/dev/null; then
    ok "WSL detected: $(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-unknown}")"
else
    warn "not detected as WSL — this script targets WSL2 Ubuntu but will continue"
fi

# --- 1. base apt packages ----------------------------------------------------
step "Base packages (apt)"
APT_PKGS=(build-essential curl wget ca-certificates git python3 python3-pip python3-venv libnotify-bin unzip)
missing=()
for p in "${APT_PKGS[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Installing: ${missing[*]}"
    if confirm "Run 'sudo apt update && sudo apt install -y ${missing[*]}'?"; then
        sudo apt-get update -qq && sudo apt-get install -y "${missing[@]}" && ok "apt packages installed"
    else
        warn "skipped apt install (you can run it manually)"
    fi
else
    ok "all base packages present"
fi

# --- 1b. GitHub CLI (gh) — not in default Ubuntu repos; use GitHub's apt repo -
step "GitHub CLI (gh)"
if command -v gh >/dev/null 2>&1; then
    ok "gh present ($(gh --version | head -n1))"
elif confirm "Install gh from GitHub's official apt repo?"; then
    sudo mkdir -p -m 755 /etc/apt/keyrings
    wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
    sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
    arch="$(dpkg --print-architecture)"
    echo "deb [arch=${arch} signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
    sudo apt-get update -qq && sudo apt-get install -y gh && ok "gh installed"
else
    warn "gh not installed (used to clone the repo)"
fi

# --- 2. systemd (WSL) --------------------------------------------------------
step "systemd"
if [[ -f /etc/wsl.conf ]] && grep -qE '^\s*systemd\s*=\s*true' /etc/wsl.conf; then
    ok "systemd already enabled in /etc/wsl.conf"
else
    if confirm "Enable systemd in /etc/wsl.conf (recommended)?"; then
        printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf >/dev/null
        warn "systemd enabled. Run 'wsl --shutdown' in Windows PowerShell, then reopen Ubuntu for it to take effect."
    else
        warn "systemd not enabled"
    fi
fi

# --- 3. uv + ruff + mypy -----------------------------------------------------
step "uv + ruff + mypy"
if ! command -v uv >/dev/null 2>&1; then
    if confirm "Install uv (astral.sh installer)?"; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # shellcheck disable=SC1091
        [[ -f "${HOME}/.local/bin/env" ]] && . "${HOME}/.local/bin/env"
        export PATH="${HOME}/.local/bin:${PATH}"
    fi
fi
command -v uv >/dev/null 2>&1 && ok "uv $(uv --version 2>/dev/null)" || warn "uv not installed"
if command -v uv >/dev/null 2>&1; then
    for tool in ruff mypy; do
        if uv tool list 2>/dev/null | grep -q "^${tool}\b"; then
            ok "${tool} already installed"
        else
            uv tool install "${tool}" >/dev/null 2>&1 && ok "${tool} installed" || warn "${tool} install failed"
        fi
    done
fi

# --- 4. Node via nvm ---------------------------------------------------------
step "Node.js (nvm)"
export NVM_DIR="${HOME}/.nvm"
if [[ ! -s "${NVM_DIR}/nvm.sh" ]] && command -v node >/dev/null 2>&1; then
    ok "node already present: $(node --version)"
else
    if [[ ! -s "${NVM_DIR}/nvm.sh" ]] && confirm "Install nvm + Node LTS?"; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    fi
    if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
        # shellcheck disable=SC1091
        . "${NVM_DIR}/nvm.sh"
        command -v node >/dev/null 2>&1 || nvm install --lts
        ok "node $(node --version 2>/dev/null)"
    else
        command -v node >/dev/null 2>&1 && ok "node $(node --version)" || warn "node not installed"
    fi
fi

# --- 5. Claude Code ----------------------------------------------------------
step "Claude Code CLI"
if command -v claude >/dev/null 2>&1; then
    CV="$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"
    version_ge "${CV:-0}" "${MIN_CLAUDE_VERSION}" \
        && ok "claude ${CV}" \
        || warn "claude ${CV:-none} < ${MIN_CLAUDE_VERSION} — run: npm install -g @anthropic-ai/claude-code@latest"
elif command -v npm >/dev/null 2>&1; then
    if confirm "Install Claude Code (npm i -g @anthropic-ai/claude-code)?"; then
        npm install -g @anthropic-ai/claude-code && ok "Claude Code installed: $(claude --version 2>/dev/null | head -n1)"
    fi
else
    warn "npm not available yet (Node step above); install Node, then: npm install -g @anthropic-ai/claude-code"
fi

# --- 6. PATH + secrets store -------------------------------------------------
step "PATH + secrets store"
# Persist ~/.local/bin in ~/.bashrc regardless of the current process PATH (this
# script exports it in-process, which would otherwise mask the need to persist).
if grep -qs '\.local/bin' "${HOME}/.bashrc"; then
    ok "PATH already persisted in ~/.bashrc"
else
    printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "${HOME}/.bashrc"
    ok "persisted ~/.local/bin to ~/.bashrc"
fi
SECRETS="${HOME}/.local/etc/secrets.env"
if [[ ! -f "${SECRETS}" ]]; then
    mkdir -p "$(dirname "${SECRETS}")" && touch "${SECRETS}" && chmod 600 "${SECRETS}"
    ok "created ${SECRETS} (mode 600)"
else
    ok "secrets store present"
fi
mkdir -p "${HOME}/cc-extensions" && ok "${HOME}/cc-extensions ready"

# --- done --------------------------------------------------------------------
step "Next steps"
cat <<'NEXT'
Prerequisites are set up.

  IMPORTANT: this shell predates the PATH/nvm changes, so uv/node/claude are not
  visible in it yet. Open a NEW terminal, OR load them into this one:

      source ~/.local/bin/env
      export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"

  Then continue:
  1. (If systemd was just enabled) run  wsl --shutdown  in Windows PowerShell,
     then reopen Ubuntu (this also reloads PATH).
  2. Authenticate Claude Code:   claude auth login      (choose your Team account)
  3. Install the rig:            ~/claude-code-rig/install/bootstrap-wsl.sh
  4. Verify:                     claude plugin list
NEXT
