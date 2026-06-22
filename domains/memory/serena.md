# serena

[serena](https://github.com/oraios/serena) is an open-source (MIT) coding
toolkit exposed as an MCP server. It gives the agent **LSP-backed semantic code
operations** — find symbol, find references, navigate by symbol, targeted
symbol-level edits — instead of brute-force file reads and text greps. It also
provides a lightweight project-memory store. Adopted as the Tier-1 retrieval
lever (`SOTA_REFRESH.md §7`); mature, local, no required egress.

> Install-deferred user action. serena is already declared in `.mcp.json`; it
> lights up once `uvx` (from `uv`) can fetch it on the target machine.

## Declared in `.mcp.json`

```json
"serena": {
  "command": "uvx",
  "args": [
    "--from", "git+https://github.com/oraios/serena",
    "serena", "start-mcp-server",
    "--context", "ide-assistant"
  ]
}
```

The `ide-assistant` context tunes serena for use alongside an agent that already
has file editing — it leans on semantic navigation and avoids redundant tools.

## Why it beats read+grep

- **Symbol-level navigation** — jump to a definition or enumerate references
  across the project via the language server, not regex guesses.
- **Targeted edits** — edit a symbol (a function/class body) precisely rather
  than diffing whole files, which keeps context small and edits surgical.
- **Scales to large repos** — the win grows with codebase size; on a small repo
  plain Read/Grep is often enough.

This is the read-side complement to the rig's write-side isolation (the
`refactor` agent's `isolation: worktree`).

## First-run setup

- Requires `uv` (provides `uvx`). serena will start the language server for the
  project's language on first use; the initial index/LSP spin-up can take a few
  seconds.
- serena reads/writes its project memory under the project (and a serena config
  dir). Treat those like any other local state — they are machine-local.

## Privacy: disable analytics (N.1.6 acceptance)

serena has an optional usage-analytics / web-dashboard feature. For a
zero-egress rig, **verify it is disabled** before relying on serena:

- Check serena's generated config (its `serena_config.yml` / project config) for
  any analytics, telemetry, or dashboard/`web` toggle and set it off.
- Confirm with `/doctor` that the MCP server starts cleanly and that no
  unexpected outbound connection is made on startup.

Record the verification in the N.1.6 checklist when you do the install.

## Keep its tool surface cheap

Like any multi-tool MCP server, serena's tool schemas are deferred by default
(MCP tool-schema deferral via `ENABLE_TOOL_SEARCH`, on unless set to `false`;
the rig pins `"true"` — see `domains/context-engineering/native-context-levers.md`),
and `mcp_trimmer.py` trims large responses. See
`core/context-budget-policy.md`.

## Relationship to native memory

serena is **retrieval/navigation**, not a replacement for native `MEMORY.md`.
Keep durable cross-session knowledge in `MEMORY.md` / `CLAUDE.md` (zero-egress,
survives `/compact`); use serena to *find and edit code* and for project-scoped
working memory. gbrain (#13) was dropped for coding use precisely because this
pairing covers it without an egress-by-default knowledge graph.

## See also

- `.mcp.json` — the server declaration.
- `core/context-budget-policy.md` — native `MEMORY.md` stance.
- `domains/context-engineering/native-context-levers.md` — `ENABLE_TOOL_SEARCH` value table + the other #27 levers.
- `skills/custom/repo-map/SKILL.md` — the breadth-first orientation map that complements serena's depth-first symbol lookup (#28).
- `domains/context-engineering/claude-context.md` — scale-gated vector search for million-LOC / fuzzy recall only; serena is the default otherwise (#29).
- `domains/scraping/playwright-mcp.md` — the other Tier-1 MCP, same cost-control notes.
