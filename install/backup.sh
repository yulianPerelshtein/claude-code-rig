#!/usr/bin/env bash
# backup.sh [output.tgz]
# Tar ~/.claude into a timestamped archive, EXCLUDING the never-leave-machine set
# (SECURITY_REVIEW.md §6): high-volume/transient state AND anything that records
# personal history, spend, clipboard, session content, org policy, or workspace
# identity. A backup tgz is exactly the artifact a user copies to another host,
# so it must not become an exfiltration path for that state. Prints the archive
# path. Refuses to write if a credential-shaped string is found in the staged set.
set -uo pipefail

CLAUDE_DIR="${HOME}/.claude"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-${HOME}/.claude.backup-${STAMP}.tgz}"

if [[ ! -d "${CLAUDE_DIR}" ]]; then
    echo "no ~/.claude directory to back up" >&2
    exit 1
fi

# Excludes are tar paths relative to CLAUDE_DIR (the `-C` root). Keep in sync with
# SECURITY_REVIEW.md §6. Grouped: high-volume/transient · personal history/spend ·
# session content · org/workspace identity · regenerable caches.
EXCLUDES=(
    # high-volume / transient
    './projects' './file-history' './todos' './shell-snapshots' './statsig'
    # credentials (never)
    './.credentials.json'
    # personal history / spend
    './history.jsonl' './cost-log.jsonl' './budget-cache.json'
    # clipboard / session content / per-session logs (inherit project names)
    './paste-cache' './backups' './compact-backups' './data' './dream-reports'
    './sessions' './tasks' './jobs' './statusline-state.json'
    # org compliance / workspace identity (names private repos + allowlist)
    './policy-limits.json' './settings.local.json'
    # regenerable caches / dev cruft
    './telemetry' './debug' './ide' './cache'
    './plugins/cache' './plugins/marketplaces'
)

# Defense-in-depth: scan the files that WILL be archived for credential-shaped
# strings (a future inline token in settings.json, a stray key file) and refuse
# rather than seal it into a portable archive. High-signal prefixes only, to keep
# false positives near zero. Build the include list as the inverse of EXCLUDES.
prune_args=()
for e in "${EXCLUDES[@]}"; do
    prune_args+=(-path "${CLAUDE_DIR}/${e#./}" -prune -o)
done
KEY_RE='ABSK[A-Za-z0-9+/=]{8,}|AKIA[0-9A-Z]{16}|\bsk-[A-Za-z0-9]{16,}|\bghp_[A-Za-z0-9]{20,}|\bxai-[A-Za-z0-9]{16,}|\bglpat-[A-Za-z0-9_-]{16,}|\bgsk_[A-Za-z0-9]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
hits=""
while IFS= read -r -d '' f; do
    if LC_ALL=C grep -aEl "${KEY_RE}" "${f}" >/dev/null 2>&1; then
        hits+="  ${f}"$'\n'
    fi
done < <(find "${CLAUDE_DIR}" "${prune_args[@]}" -type f -print0 2>/dev/null)

if [[ -n "${hits}" ]]; then
    echo "REFUSING to back up — credential-shaped strings found in:" >&2
    printf '%s' "${hits}" >&2
    echo "Remove or relocate the secret (e.g. to ~/.config/claude/), then retry." >&2
    exit 2
fi

tar_excludes=()
for e in "${EXCLUDES[@]}"; do
    tar_excludes+=("--exclude=${e}")
done

tar "${tar_excludes[@]}" -czf "${OUT}" -C "${CLAUDE_DIR}" .

echo "backup written: ${OUT}"
