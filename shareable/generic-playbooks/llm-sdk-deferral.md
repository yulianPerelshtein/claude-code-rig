# LLM SDK deferral

When the LLM provider is still in flux (or optional), don't let its SDK or API
key be a hard import-time dependency.

## Pattern

- **Import the SDK inside the function** that needs it, not at module top. The
  module then loads cleanly without the dependency installed, and CI without
  the key still passes.
- If the key or SDK is missing at call time, return a clear error (e.g. HTTP
  503) rather than crashing.
- Keep `LLM_BASE_URL` / `LLM_MODEL` overridable via env so you can swap
  providers without code changes. Many providers (e.g. OpenAI-compatible
  endpoints) work with the `openai` package and a `base_url` override instead
  of a bespoke SDK.

## CI defence

Beyond per-test `monkeypatch.delenv`, set the key to an empty string in the CI
job's `env:` block:

```yaml
env:
  LLM_API_KEY: ""
```

This defends against a future test forgetting to mock, a dropped monkeypatch, or
CI accidentally depending on a live third-party service.

## load_dotenv ordering

If you use `dotenv`, call `load_dotenv()` **before** importing app modules that
read env vars at import time:

```python
from dotenv import load_dotenv
load_dotenv()
from app import service  # noqa: E402
```

It's a no-op in production (env injected directly) but prevents import-time reads
from seeing an unset variable in local/dev runs.
