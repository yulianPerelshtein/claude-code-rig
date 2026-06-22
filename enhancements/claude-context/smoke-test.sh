#!/usr/bin/env bash
# Smoke test for the `claude-context` enhancement (Tier 2, opt-in, scale-gated).
# Run AFTER adding the MCP with the MANDATORY zero-egress config (local Ollama
# embeddings + local Milvus). See domains/context-engineering/claude-context.md.
set -euo pipefail

fail=0

if ! command -v node >/dev/null 2>&1 || \
   [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -lt 20 ]; then
    echo "claude-context: needs Node.js >= 20 (the MCP runtime). NOT satisfied." >&2
    fail=1
fi

if command -v claude >/dev/null 2>&1 && claude mcp list 2>/dev/null | grep -q "claude-context"; then
    echo "claude-context: MCP registered."
else
    echo "claude-context: MCP NOT registered. Add it (deferred user action):" >&2
    echo '  claude mcp add claude-context -e EMBEDDING_PROVIDER=Ollama \' >&2
    echo '    -e MILVUS_ADDRESS=localhost:19530 -- npx @zilliz/claude-context-mcp@latest' >&2
    fail=1
fi

# Zero-egress backends (local Ollama embeddings + local Milvus) must both be
# reachable, else the tool falls back to hosted defaults and egresses your code.
# Use a raw TCP connect (bash /dev/tcp): curl misreads Milvus's gRPC port, and a
# TCP open is all we need to confirm "something local is listening".
probe() {  # host port
    (exec 3<>"/dev/tcp/$1/$2") 2>/dev/null
}

if probe localhost 11434; then
    echo "ollama: reachable at localhost:11434 (local embeddings)."
else
    echo "ollama: NOT reachable at localhost:11434 — required for zero egress." >&2
    fail=1
fi

if probe localhost 19530; then
    echo "milvus: reachable at localhost:19530 (local vector store)."
else
    echo "milvus: NOT reachable at localhost:19530 — required for zero egress." >&2
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "Reminder: serena is the default for exact lookup; repo-map for orientation." >&2
    echo "Only enable claude-context for million-LOC / fuzzy-recall repos, fully local." >&2
    exit 1
fi
echo "claude-context: OK (Node + MCP registered; local Ollama + Milvus reachable)."
