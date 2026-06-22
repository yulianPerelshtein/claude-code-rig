---
name: context-engineering
description: >-
  Token-economy and context-shaping knowledge — native reduction first (prompt
  caching, context editing, compaction), then opt-in tools. Use when reducing
  token spend, evaluating a compression layer, or shaping model context.
---

# context-engineering

How to spend fewer tokens for the same work. **Native levers first** (see
`core/context-budget-policy.md` and `native-context-levers.md`): prompt caching,
context editing, auto-compaction, skills lazy-loading, MCP tool-schema deferral
(`ENABLE_TOOL_SEARCH`, on by default). Evaluate any third-party
token-economy tool against those before adopting it.

Tier-2 opt-in tools documented here: `headroom.md` (a wrapping compression layer
— pre-1.0, data-loss caveats, realistic ~47% on codebase work) and
`claude-context.md` (scale-gated vector code search — local Ollama + Milvus for
zero egress; off unless the repo is million-LOC / fuzzy-recall).
`toon-output-format.md` (Tier 3) is a compact tabular output encoding — ~40% on
*uniform tabular* data only (CSV wins for flat tables, JSON for nested), narrow
use.
