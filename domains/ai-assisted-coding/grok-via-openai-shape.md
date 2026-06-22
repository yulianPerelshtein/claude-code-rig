# Grok / xAI via the OpenAI-compatible client

xAI/Grok exposes an OpenAI-compatible API. Use the `openai` package with a
`base_url` override — not a bespoke SDK and not the Anthropic shape.

```python
from openai import OpenAI
client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
resp = client.chat.completions.create(model="grok-3-mini", messages=[...])
```

- Env: `XAI_API_KEY` (matches the xAI console naming). Keep optional
  `LLM_BASE_URL` + `LLM_MODEL` overrides so the same code runs against OpenAI,
  OpenRouter, or a local server.
- Free-tier model availability rotates — verify model names against the
  provider console rather than hard-coding assumptions.
