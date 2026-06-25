---
name: memory
description: >-
  Semantic code retrieval and project memory via the serena MCP (LSP-backed
  symbol navigation), on top of native MEMORY.md. Use when navigating a large
  codebase by symbol, doing precise find-references/edits, or persisting project
  knowledge across sessions.
---

# memory

The rig's coding-memory and code-navigation layer. Read `serena.md` for the
serena MCP server (the locked Tier-1 retrieval lever, `SOTA_REFRESH.md §7`).

serena complements — does not replace — the **native** memory backbone:
`MEMORY.md` (machine-local, zero-egress, survives `/compact`) and `CLAUDE.md`
(see `domains/context-engineering/native-context-levers.md`). gbrain was **dropped** for coding use;
serena + native `MEMORY.md` cover it without an egress-by-default dependency.
