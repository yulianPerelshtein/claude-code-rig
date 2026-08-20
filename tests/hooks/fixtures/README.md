# Hook payload fixtures

Captured from live sessions, then sanitised. **Do not hand-edit the structure.**

These exist because hand-authored fixtures encode the same assumption as the
code under test, so they cannot detect a wrong assumption. When
`read_injection_scanner.py` read a top-level `tool_response.content` — a key
neither `Read` nor `WebFetch` sends — ten hand-written tests passed against a
hook that extracted the empty string and had never scanned a byte.

## The shapes

| Tool | Where the text lives |
|---|---|
| `Read` | `tool_response.file.content` (alongside `filePath`, `numLines`, `startLine`, `totalLines`) |
| `WebFetch` | `tool_response.result` (alongside `bytes`, `code`, `codeText`, `durationMs`, `url`) |

Neither has a top-level `content`. `WebFetch.result` is the model's *summary*
of the page, not the raw bytes — scanning it is still correct, because the
summary is what enters context, but it will not catch an injection that failed
to survive summarisation.

## Rebuilding

```bash
tools/capture-hook-payloads.sh
uv run --with pytest --with pyyaml pytest tests/hooks/ -q
```

The script drives a real headless session, sanitises every machine-identifying
value (paths, session/prompt/tool ids), and refuses to finish if the result
fails the redaction gate. Raw captures never reach the repo — they carry
absolute paths, and therefore the username.

`test_read_fixture_nests_content_under_file` and
`test_webfetch_fixture_uses_result` pin the captured structure. If Claude Code
changes a response shape, those fail loudly — which is the point. Re-capture
rather than editing the JSON by hand.

## Gotcha

An untrusted workspace silently drops `permissions.allow` from a project
`settings.json`, so the capture script grants tools with `--allowedTools`
instead. Using `permissions.allow` there produces an empty capture and a
confusing "permission hasn't been granted" message.
