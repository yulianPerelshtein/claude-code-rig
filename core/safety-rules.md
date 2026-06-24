# Safety rules

## Destructive operations

- NEVER run destructive or irreversible commands without explicit user
  confirmation.
- NEVER read `.env`, `.secrets`, credential files, or anything matching a
  secret pattern.
- NEVER `git push --force` or `git reset --hard` without explicit confirmation.
- NEVER force-push to `main`/`master`; warn the user if asked.

## GitHub actions

- NEVER post comments, reviews, or any content to GitHub (PRs, issues, gists,
  etc.) without explicit user confirmation for each action.

## Filesystem isolation (WSL)

- Keep working trees, builds, and dependencies on the Linux filesystem. The
  Windows mount (`/mnt/<drive>/`) is cross-OS and slow (9p protocol) — never run
  a repo, build, or package install there.
- Crossing to `/mnt/c` is legitimate only for handing a finished artifact to a
  Windows-native tool (e.g. a USD viewer, Revit). The guardrail prompts for
  confirmation on such writes rather than performing them silently.

## Enforcement

- The Bash guardrail (`hooks/blocked-commands.json` + `pre-tool/guardrail.py`,
  wired as a PreToolUse hook) rejects blocked command patterns automatically
  (e.g. `ruff format`, force-push) and prompts for confirmation on `/mnt/c`
  access. Treat a guardrail rejection as a hard stop, not a prompt to find a
  workaround.
