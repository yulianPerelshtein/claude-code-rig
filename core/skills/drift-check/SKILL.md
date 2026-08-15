---
name: drift-check
description: Detect instruction drift and duplication between the user and project CLAUDE.md layers
disable-model-invocation: true
---

Detect instruction drift — directives duplicated across the user layer and
project layers, which should live in exactly one place (per
`context-architecture.md`).

Steps:

1. **Discover the instruction files that actually exist**, then grep them.
   Do not assume a fixed repo home — this skill previously hardcoded
   `~/workspace/*/.claude/CLAUDE.md`, which existed on no machine, so the grep
   matched nothing and the skill reported "no drift" every time it ran:

   ```bash
   # Every instruction file Claude Code would load, wherever repos actually live.
   # Excluded: third-party clones (cc-extensions) and worktrees, whose files are
   # someone else's layers or a second copy of one already counted — both would
   # report duplication that is not yours to fix.
   mapfile -t LAYERS < <(
     {
       printf '%s\n' "${HOME}/.claude/CLAUDE.md"
       find "${HOME}" -maxdepth 4 \( -name CLAUDE.md -o -name AGENTS.md \) \
         -not -path '*/.git/*' -not -path '*/node_modules/*' \
         -not -path '*/.venv/*' -not -path "${HOME}/.claude/plugins/*" \
         -not -path "${HOME}/cc-extensions/*" -not -path "${HOME}/.claude-worktrees/*" \
         2>/dev/null
     } | sort -u
   )
   printf 'scanning %d instruction file(s):\n' "${#LAYERS[@]}"
   printf '  %s\n' "${LAYERS[@]}"

   grep -rh "NEVER\|Do NOT\|must be" "${LAYERS[@]}" 2>/dev/null \
     | sed 's/^[[:space:]]*//' | sort | uniq -d
   ```

   **Report the file list before the findings.** If it holds only one entry
   there is nothing to compare, and "no duplication" would be a vacuous pass
   rather than a real result — say so explicitly instead.

2. For each phrase that appears in 2+ files: it belongs in the **user** layer
   only — recommend removing it from the project layer(s) so there is one source
   of truth.

3. Also report:
   - Project `CLAUDE.md`/`AGENTS.md` files that restate user-layer safety rules.
   - Any directive that contradicts another across layers (flag for the user to
     resolve — do not auto-edit).

4. Output a short diff-style summary: phrase, the files it appears in, and the
   recommended single home. Do **not** modify any file; this is advisory.
