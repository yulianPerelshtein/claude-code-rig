# claude-context (vector code search) — Tier 2, scale-gated, opt-in

[claude-context](https://github.com/zilliztech/claude-context) (`@zilliz/claude-context-mcp`)
is an MCP that adds **hybrid semantic code search** (BM25 + dense vector) over an
indexed codebase, with AST-based chunking and Merkle-tree incremental re-indexing.
MIT, Zilliz-backed, Node ≥ 20. It is **strictly opt-in and scale-gated** in this
rig (`profiles/enhanced-tier2.yaml`) — most repos should **not** enable it.

> Install + the local backends are **deferred user actions**. This doc + the
> `enhanced-tier2.yaml` entry make the opt-in *available*; they do not enable it.
> The installer validates and reports it but never runs the install.

## When it beats serena (and when it doesn't)

serena is the **default** code-retrieval MCP (`domains/memory/serena.md`): exact,
LSP-backed symbol lookup and edits. claude-context is only worth the infra when:

- the repo is **larger than serena's LSP working set can hold** (≈ million-LOC
  monorepos), or
- you need **fuzzy recall** — "where is the thing that does X?" — across a huge
  codebase where you don't know the symbol name.

For exact symbol/reference lookup, **serena wins** — keep claude-context off by
default. For up-front *orientation* of an unfamiliar repo, use the local
`repo-map` skill (`skills/custom/repo-map/`) instead — it needs no index or infra.
claude-context's own evaluation reports **~40% token reduction at equivalent
retrieval quality** on large codebases; on small ones its indexing infra is pure
overhead.

| | serena (default) | repo-map | claude-context (scale-gated) |
|---|---|---|---|
| Mechanism | LSP symbols | tree-sitter + PageRank | vector + BM25 index |
| Best at | exact symbol / refs | orientation map | fuzzy recall at huge scale |
| Infra | none (uvx) | none (uv) | **Milvus + embeddings + index** |
| Default | on | on-demand | **off** |

## Mandatory zero-egress configuration

The project's default config uses **hosted OpenAI embeddings + Zilliz Cloud** —
that **egresses your code**. The rig requires the documented **fully local**
deployment instead, so nothing leaves the machine:

- **Embeddings → local Ollama** (`EMBEDDING_PROVIDER=Ollama`, a local embedding
  model such as `nomic-embed-text`). Exact Ollama host/model env-var names: see
  the project's [Environment Variables Guide](https://github.com/zilliztech/claude-context/blob/master/docs/getting-started/environment-variables.md)
  — set them, don't guess.
- **Vector store → local Milvus** (`MILVUS_ADDRESS=localhost:19530`, no cloud
  token). Run Milvus locally (e.g. `milvus-standalone` via Docker).

If you can't run a local Milvus + Ollama, **do not enable this** — falling back to
the hosted defaults would ship your codebase to third parties, which the rig's
zero-egress stance forbids.

## Install shape (deferred user action)

```bash
# 1. local backends first: Ollama (with an embedding model pulled) + local Milvus.
# 2. add the MCP pointed at BOTH locals (no OpenAI key, no Zilliz token):
claude mcp add claude-context \
  -e EMBEDDING_PROVIDER=Ollama \
  -e MILVUS_ADDRESS=localhost:19530 \
  -- npx @zilliz/claude-context-mcp@latest
# (+ the Ollama host/model env vars from the Environment Variables Guide)
```

Then in a session: "Index this codebase" → "Check the indexing status" → search
with natural-language queries. Re-indexing is incremental (Merkle tree). Verify
with `enhancements/claude-context/smoke-test.sh`.

## Why opt-in / the risks

- **Infra + staleness** — a vector index drifts from the code; you own re-indexing
  and the Milvus/Ollama services. Medium operational risk → off by default.
- **Cost shape** — high ROI on million-LOC repos, **zero on small ones** (pure
  overhead). Gate on repo size.
- **Mutually fine with serena** — they're complementary, not conflicting; no
  `conflicts_with`. Keep serena primary.

## See also

- `domains/memory/serena.md` — the default; prefer it for exact lookup.
- `skills/custom/repo-map/SKILL.md` — zero-infra orientation map (try this first).
- `domains/context-engineering/native-context-levers.md` — native context trims
  to apply before reaching for an index.
- `profiles/enhanced-tier2.yaml` / `manifests/marketplace.yaml#enhancements` — the
  opt-in wiring.
