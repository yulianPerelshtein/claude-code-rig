# Repo map — ranked orientation for unfamiliar code

A local, zero-egress **orientation map** of a repository: the definitions most
central to the codebase, ranked and token-budgeted. It's the always-on breadth
map that complements serena's precise, on-demand depth lookups. Operationalized
by the `repo-map` skill (`skills/custom/repo-map/`).

## Why it exists

Dropping into an unfamiliar or large repo, the first problem is *where to look*.
Grep finds strings; serena answers "show me symbol X"; neither gives you the
shape of the whole repo. The repo-map does — a compact, ranked list of the
functions/classes/types other code depends on most, so you start at the load-
bearing parts instead of a random file.

## How it works (Aider's algorithm, local)

1. **Tags** — tree-sitter parses each file and a per-language tag query marks
   every identifier as a *definition* or a *reference*.
2. **Graph** — a file-reference graph: an edge `referencer → definer`, weighted
   by how many of the definer's symbols the referencer uses.
3. **PageRank** — weighted PageRank ranks files by centrality, with a **task-aware
   personalization vector** that biases toward your `--focus` files and recently
   touched files (so the map orients around what you're working on).
4. **Budgeted render** — rank flows to symbols (boosted by repo-wide reference
   count); the top ones are greedily selected until a ~1k-token budget, rendered
   as signatures only (bodies elided).
5. **Cache** — per-file tags are cached on mtime, so re-runs only re-parse what
   changed.

Implemented self-contained (no numpy/scipy/networkx; PageRank is a power
iteration) so the on-demand `uv run` cold-start stays cheap, and with no
dependency on the stale `grep-ast`.

## vs serena (complementary, not competing)

| | repo-map | serena |
|---|---|---|
| Direction | Breadth — orientation | Depth — precise lookup |
| Answers | "What's central here?" | "Where is symbol X / its refs?" |
| When | First, on an unfamiliar repo | Once you know what to chase |
| Cost | One ranked map, token-budgeted | Per-query |

Use the map to choose targets; use serena/Read to go deep on them.

## Workflow

1. Run the `repo-map` skill at the repo root, passing the task's files as
   `--focus` for task-aware ranking.
2. Read the top entries — these are the load-bearing definitions. Note the files
   that recur.
3. Dive into the chosen symbols' bodies with **serena** (`find_symbol`) or
   **Read**.
4. For a parallel investigation, use the map to scope what each agent looks at
   (`parallel-agent-fan-out.md`).

## Extending the language set

Launch coverage is Python, JavaScript/JSX, TypeScript/TSX. To add a language: add
its `tree-sitter-<lang>` grammar to the `uv run --with` list, map its extension in
`LANG_BY_EXT`, and add a tag-pattern block in `TAG_PATTERNS` (each pattern is
compiled independently, so a pattern that's invalid for a grammar is dropped
rather than breaking the language). See `skills/custom/repo-map/repo_map.py`.

## See also

- `skills/custom/repo-map/SKILL.md` — how to invoke it.
- `domains/memory/serena.md` — the depth-first counterpart.
- `domains/context-engineering/native-context-levers.md` — keeping MCP/context
  cost low alongside this.
