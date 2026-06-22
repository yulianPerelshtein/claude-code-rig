# Lazy LLM-SDK import / provider deferral

When the LLM provider is still in flux, import the SDK **inside** the function
and fail soft if key or SDK is missing. The module then loads cleanly without
the dependency, and CI without it still passes.

```python
def call_llm(...):
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise HTTPException(503, "LLM key not configured")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise HTTPException(503, "LLM SDK not installed") from exc
    ...
```

This avoids committing to a `pyproject.toml` provider dependency before the
provider choice is final, while keeping the route honest (clear 503) at runtime.
