---
name: drift-check
description: Detect instruction drift and duplication between the user and project CLAUDE.md layers
disable-model-invocation: true
---

Detect instruction drift — directives duplicated across the user layer and
project layers, which should live in exactly one place (per
`context-architecture.md`).

Steps:

1. Run the duplication grep across the user and project instruction files:

   ```bash
   grep -rh "NEVER\|Do NOT\|must be" \
     ~/.claude/CLAUDE.md ~/workspace/*/.claude/CLAUDE.md 2>/dev/null \
     | sed 's/^[[:space:]]*//' | sort | uniq -d
   ```

   (Adjust the project glob to wherever the user keeps repos.)

2. For each phrase that appears in 2+ files: it belongs in the **user** layer
   only — recommend removing it from the project layer(s) so there is one source
   of truth.

3. Also report:
   - Project `CLAUDE.md`/`AGENTS.md` files that restate user-layer safety rules.
   - Any directive that contradicts another across layers (flag for the user to
     resolve — do not auto-edit).

4. Output a short diff-style summary: phrase, the files it appears in, and the
   recommended single home. Do **not** modify any file; this is advisory.
