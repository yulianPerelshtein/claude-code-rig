# Editing a PR body: use the REST API, not the CLI

`gh pr edit --body` can silently fail to update a PR body on some org
configurations — it exits 0 and prints a deprecation message, but the body is
unchanged. Never trust the exit code alone.

## Reliable approach

Use the REST API and verify the result:

```bash
# Write the new body to a JSON payload.
printf '{"body": %s}' "$(jq -Rs . < body.md)" > p.json

# PATCH the pull request.
gh api -X PATCH repos/<owner>/<repo>/pulls/<number> --input p.json

# Verify the body actually changed (don't trust exit code).
gh api repos/<owner>/<repo>/pulls/<number> --jq .body
```

## Notes

- The same caution applies to other `gh` mutations that wrap deprecated
  endpoints — confirm the change via a follow-up read (`--jq`).
- To read review comments on a PR: `gh api repos/<owner>/<repo>/pulls/<n>/comments`.
