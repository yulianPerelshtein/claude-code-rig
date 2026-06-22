# AI-as-judge testing

When you use an LLM to grade or classify outputs ("LLM as judge"), split the
parsing from the call so the logic is unit-testable without a live model.

## Pattern

- `_parse_<thing>(raw) -> result` — a **pure** function that turns the model's
  raw text into a structured result. Test it against canned outputs, including
  every fail-open case (empty string, truncated JSON, unexpected shape).
- `grade_<thing>(...)` — does the env / SDK / request plumbing, then calls the
  parser. Keep it thin.

Unit tests cover the parser exhaustively. **Live-LLM evaluation belongs in a
separate harness**, not in the unit-test suite — it's non-deterministic, costs
money, and depends on a third-party service.

## Why

- Deterministic, fast tests that don't hit the network or burn tokens.
- Fail-open behaviour is verified explicitly, so a malformed model response
  degrades gracefully instead of throwing.
- The judge prompt can change without rewriting the parser tests.
