# Laptop setup — fresh Windows to a working rig

End-to-end setup for installing the rig on a **fresh Windows laptop** with no WSL
yet, through to validation. Docker is **not** required for the rig or its
validation. There are **two separate logins**: GitHub (to clone this repo)
and Claude Code (your Claude.ai account).

For an already-working WSL2 Ubuntu, skip to step 4.

---

## 1. Windows: install WSL2 + Ubuntu

In an **Administrator PowerShell** (requires Windows 10 2004+ or Windows 11):

```powershell
wsl --install -d Ubuntu-24.04
```

Reboot if prompted. On first launch, Ubuntu asks you to create a UNIX username +
password. Then confirm WSL2:

```powershell
wsl --status        # Default Version: 2
wsl -l -v           # Ubuntu-24.04 should show VERSION 2
```

Everything from here runs **inside the Ubuntu shell**, never in `/mnt/c`.

## 2. Ubuntu: get git + gh and authenticate to GitHub

`git` is in the default repos; `gh` is **not** — install it from GitHub's
official apt repo (don't use snap, which needs systemd):

```bash
sudo apt update && sudo apt install -y git wget

# GitHub CLI from its official apt repo
sudo mkdir -p -m 755 /etc/apt/keyrings
wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
sudo apt update && sudo apt install -y gh

gh auth login       # GitHub.com > HTTPS > Login with a web browser; use the
                    # your GitHub account (the repo is public, so any account works).
                    # This is NOT your Claude login.
```

## 3. Ubuntu: clone the rig

```bash
gh repo clone yulianPerelshtein/claude-code-rig ~/claude-code-rig
```

## 4. Ubuntu: install prerequisites

```bash
~/claude-code-rig/install/setup-laptop.sh
```

This installs base packages, Python, Node (via nvm), `uv` + `ruff` + `mypy`, and
Claude Code; enables systemd; and ensures `~/.local/bin` on PATH + the secrets
store. It is idempotent.

**Then reload your shell** so the freshly installed tools are on PATH (the
current shell predates them) — open a new terminal, or:

```bash
source ~/.local/bin/env
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
for c in uv ruff mypy node claude; do command -v "$c" >/dev/null && echo "OK $c" || echo "MISSING $c"; done
```

If `setup-laptop.sh` enabled **systemd**, run `wsl --shutdown` in Windows
PowerShell and reopen Ubuntu (that reload covers PATH too).

## 5. Ubuntu: authenticate Claude Code + install the rig

```bash
claude auth login        # choose your Claude.ai Team account
claude --version         # must be >= 2.1.80
~/claude-code-rig/install/bootstrap-wsl.sh   # preflight + marketplace install
claude plugin list       # claude-code-rig@claude-code-rig should be enabled
```

`bootstrap-wsl.sh` runs the env preflight, then
`claude plugin marketplace add ~/claude-code-rig` + `claude plugin install`.

## 6. Validation

Open a Claude Code session in any project and confirm:

- [ ] `claude plugin list` shows `claude-code-rig` **enabled**
- [ ] Slash skills resolve: `/commit`, `/health`, `/review-pr`, `/save-state`,
  `/walkthrough`, `/wrap-up`
- [ ] The guardrail blocks a destructive command (e.g. ask it to run
  `rm -rf /tmp/x` — the `PreToolUse` hook denies it)
- [ ] `/agents` lists `code-reviewer`, `pr-writer`, `refactor`, `test-writer`
- [ ] `/doctor` shows no fatal plugin errors. The `serena` and `playwright` MCP
  servers reporting **"binary not found"** is **expected** until you install
  those servers (optional, opt-in) — not a failure.

### Optional: `rate_limits` probe

On a Team-OAuth session, check whether the statusline stdin carries `rate_limits`
(if so, the dashboard can drop its OAuth fallback). Temporary probe:

```bash
cat > ~/.claude/_rl_probe.sh <<'EOF'
#!/usr/bin/env bash
cat > ~/.claude/_rl_stdin.json
echo "rl-probe"
EOF
chmod +x ~/.claude/_rl_probe.sh
```

Temporarily set `"statusLine": {"type": "command", "command": "~/.claude/_rl_probe.sh"}`
in `~/.claude/settings.json`, start a session, send one prompt, then:

```bash
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude/_rl_stdin.json'))); print('rate_limits PRESENT' if 'rate_limits' in d else 'rate_limits absent')"
```

Revert the `statusLine` change and remove the probe files afterward. Record the
result — it decides the dashboard's fallback.

## 7. Rollback

```bash
claude plugin uninstall claude-code-rig@claude-code-rig
claude plugin marketplace remove claude-code-rig
```

The rig installs as a **plugin** (nothing is copied into `~/.claude`), so removal
is clean. The bespoke `install/install-profile.sh` path (which does copy into
`~/.claude`, with backups) is only for a DLP-locked machine that cannot use the
marketplace.

---

## Notes

- **Two logins, don't confuse them:** `gh auth login` = GitHub (repo access);
  `claude auth login` = Claude.ai (Team/Pro/Max).
- **Docker:** not needed for the rig or its validation. Add it later only for
  your own containerized work.
- **WSL discipline:** never read or write under `/mnt/c` from the Ubuntu side —
  the guardrail enforces this once the rig is installed.
