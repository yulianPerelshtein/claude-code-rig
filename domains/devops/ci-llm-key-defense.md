# CI: LLM-key empty-string defense-in-depth

Per-test `monkeypatch.delenv("LLM_API_KEY")` only covers the test that calls it.
Also set the key to an empty string in the CI job's `env:` block:

```yaml
- name: Run pytest
  run: uv run pytest -q
  env:
    LLM_API_KEY: ""        # provider-specific name, e.g. XAI_API_KEY / OPENAI_API_KEY
```

This is belt-and-suspenders against:

- a future test that forgets to mock the key,
- a refactor that drops the monkeypatch,
- CI accidentally depending on a live third-party service being up.

Green builds should prove code correctness, not API availability.
