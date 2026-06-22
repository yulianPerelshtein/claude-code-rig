# GitHub CLI: use REST for PR body/title

`gh pr edit --body "..."` can **silently fail** to update a PR body on some org
configurations — it exits `0` with a deprecation message that reads like a
warning but means the update did not apply. Don't trust the exit code.

Reach for the REST API first for body/title updates:

```bash
python3 -c "import json,sys; json.dump({'body': open('/tmp/body.md').read()}, open('/tmp/p.json','w'))"
gh api -X PATCH repos/<owner>/<repo>/pulls/<n> --input /tmp/p.json \
  --jq '{updated_at, first_line: (.body | split("\n")[0])}'
```

- Building the JSON in Python and passing `--input` avoids shell quoting / JSON
  escaping mistakes for multi-line bodies.
- For short single-line bodies, `--field body="..."` works too.
- **Verify with the `--jq` output**, never trust exit code alone.
