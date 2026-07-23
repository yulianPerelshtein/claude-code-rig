#!/usr/bin/env bash
# qn — quick-capture a timestamped bullet into today's Obsidian daily note.
#
# Single source of truth for quick-note capture: the interactive `qn` shell
# function, a personal `/qn` command, and the rig's `qn` skill all call this, so
# the logic lives in exactly one place.
#
# Vault: $RIG_VAULT_DIR, else ~/notes. A missing daily note is scaffolded from
# the vault's own _templates/daily.md when present, so a note created by qn is
# identical to one Obsidian would create (previously qn wrote a stunted note
# with only a "## Log" heading); otherwise a minimal heading + "## Log".
set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "qn: nothing to capture (usage: qn <text>)" >&2
    exit 2
fi

vault="${RIG_VAULT_DIR:-$HOME/notes}"
if [ ! -d "$vault" ]; then
    echo "qn: vault not found at $vault (set RIG_VAULT_DIR)" >&2
    exit 1
fi

today="$(date +%F)"
note="$vault/daily/$today.md"
template="$vault/_templates/daily.md"

mkdir -p "$vault/daily"

if [ ! -f "$note" ]; then
    if [ -f "$template" ]; then
        # Obsidian core-template placeholders; anything else passes through
        # untouched (a Templater-driven vault can still post-process it).
        sed -e "s/{{date:YYYY-MM-DD}}/$today/g" \
            -e "s/{{date}}/$today/g" \
            -e "s/{{title}}/$today/g" \
            "$template" >"$note"
    else
        printf '# %s\n\n## Log\n' "$today" >"$note"
    fi
fi

# The bullet is appended at EOF, which lands under "## Log" because that is the
# last section in the template. Add the heading if a hand-made note lacks it.
grep -qE '^## Log[[:space:]]*$' "$note" || printf '\n## Log\n' >>"$note"

printf -- '- %s %s\n' "$(date +%H:%M)" "$*" >>"$note"
echo "$note"
