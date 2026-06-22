# Safety rules

These are hard guardrails. They apply in every session, at every layer.

## Destructive operations

- NEVER run destructive or irreversible commands without explicit user
  confirmation.
- NEVER read `.env`, `.secrets`, credential files, or anything matching a
  secret pattern.
- NEVER `git push --force` or `git reset --hard` without explicit confirmation.
- NEVER force-push to `main`/`master`; warn the user if asked.
- Run local tests before declaring a feature complete.

## GitHub actions

- NEVER post comments, reviews, or any content to GitHub (PRs, issues, gists,
  etc.) without explicit user confirmation for each action.

## Filesystem isolation (WSL)

- NEVER read or write the Windows filesystem mount (the `/mnt/<drive>/` path).
  All work stays on the Linux filesystem.
- Use the `workdir` parameter to change directories; avoid `cd <dir> && <cmd>`.

## Enforcement

- The Bash guardrail (`hooks/blocked-commands.json`, wired as a PreToolUse
  hook) rejects blocked command patterns automatically (e.g. `ruff format`,
  force-push). Treat a guardrail rejection as a hard stop, not a prompt to
  find a workaround.
