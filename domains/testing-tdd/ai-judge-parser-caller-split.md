# LLM-as-judge: parser / caller split

When implementing an LLM grader/judge (e.g. a hallucination/groundedness
grader), split the JSON parsing from the LLM call into two functions:

```python
def _parse_grader_response(raw: str) -> tuple[bool, str]:
    """Pure. No network. Testable against canned LLM outputs."""
    ...

def grade_groundedness(inputs) -> tuple[bool, str]:
    api_key = os.environ.get("LLM_API_KEY")        # env lookup
    ...                                            # SDK import + request
    return _parse_grader_response(raw)             # then parse
```

- Unit-test the **parser** comprehensively: grounded path, ungrounded path,
  markdown-fence wrapping, malformed JSON, missing fields, empty response — all
  the fail-open behaviors — **without ever calling the LLM**.
- Live-LLM evaluation belongs in a separate eval harness, not the unit suite
  (which should prove code correctness, not model behaviour or API uptime).
