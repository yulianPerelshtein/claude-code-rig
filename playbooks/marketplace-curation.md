# Marketplace curation — which plugins to actually install (#23)

A standing shortlist of Claude Code marketplace plugins worth installing for a
coding rig, plus the long tail to skip. **Tier-2 / curation only**: installing
any of these is a user decision, not something the rig auto-enables. Source
survey: `SOTA_REFRESH.md §4.6`.

> The rig's *own* capabilities (skills, agents, hooks) ship via the plugin in
> this repo. This list is about **third-party marketplace plugins** you add on
> top, from `claude-plugins-official` and other marketplaces.

## Already wired by the rig (don't re-add)

These are declared in `.mcp.json` / `manifests/marketplace.yaml` — installed on
the normal path, so they're not "new" picks:

- **serena** (MCP) — semantic LSP code search/edit (`.mcp.json`, `domains/memory/serena.md`).
- **Playwright MCP** — default browser automation (`.mcp.json`).
- **skill-creator**, **playwright**, **typescript-lsp**, **frontend-design**
  (`@claude-plugins-official`, in `marketplace.yaml#plugins`).

## Worth installing (evaluate, then opt in)

| Plugin | Why | Notes |
|---|---|---|
| **pr-review-toolkit** / **code-review** | Structured PR/diff review beyond the rig's `code-reviewer` agent | Pair with, don't replace, the rig's review flow; cost-gate per `requesting-code-review`. |
| **security-guidance** (+ **semgrep**, **sonarqube**) | SAST + secure-coding guidance; complements the native `/security-review` | Rescoped #20 covers *config* audit (`domains/security/`); these cover code-level SAST. |
| **plugin-dev** | Authoring/validating plugins — useful since the rig *is* a plugin | Complements `skill-creator` (already wired). |
| **langfuse-observability** | The easy path to an OTel backend for traces/metrics | Pairs with `domains/observability/claude-code-otel.md`; self-hosted Langfuse = zero-egress. |

## Skip (thin or redundant here)

- **`claude-md-management`, `hookify`, `code-simplifier`** — superpowers + the
  rig's own hooks/agents already cover these; net new surface for little gain.
- **SaaS long-tail plugins** — anything that's a thin wrapper around a paid
  hosted service. Prefer a local/native equivalent first (the rig's standing
  bias, `domains/context-engineering/native-context-levers.md`).

## How to vet a marketplace plugin before installing

1. **Does the rig already cover it?** Check `.mcp.json`, the rig's skills/agents,
   and superpowers first — most "productivity" plugins duplicate those.
2. **Egress?** Prefer plugins that run locally or against a self-hosted backend;
   treat anything that ships code/prompts to a third party as opt-in only.
3. **Maintenance + trust.** Recent commits, real maintainer, sane star:watcher
   ratio (`SOTA_REFRESH.md §5` flags star-inflated repos). Pin the version.
4. **Cost.** Some plugins (e.g. anything wrapping the API in CI) bill your
   account — see `playbooks/ci/claude-in-ci.md`.
5. **Validate** with `claude plugin validate` / `/hooks` / `/skills` after adding,
   and remove what you don't use (every loaded plugin is recurring context).

## See also

- `manifests/marketplace.yaml` — what the rig pins/installs today.
- `domains/memory/serena.md`, `domains/observability/claude-code-otel.md` — the
  flagship MCP + the observability backend these picks complement.
- `domains/context-engineering/native-context-levers.md` — keep added plugins'
  context cost low (`ENABLE_TOOL_SEARCH`).
