# headroom (token compression) — Tier 2, opt-in

[headroom](https://github.com/chopratejas/headroom) is a context-compression
layer that sits **between Claude Code and the Anthropic API** and claims 60–95%
token reduction. It ships as a library, an MCP server, and a `headroom wrap
claude` drop-in wrapper (Apache-2.0). It is **strictly opt-in** in this rig
(`profiles/enhanced-tier2.yaml`), downgraded from Tier 1 per `SOTA_REFRESH.md
§4.3` — read the caveats below before enabling it.

> Install + evaluation are **deferred user actions** (laptop, ≥1 week real-world
> use). This doc + the `enhanced-tier2.yaml` entry make the opt-in *available*;
> they do not enable it.

## Read the workload caveat first

The headline "60–95%" is **workload-selective**. headroom's own proof table:

| Workload | Reduction |
|---|---|
| **Codebase exploration** (most rig-relevant) | **~47%** |
| GitHub issue triage | ~73% |
| SRE / code-search | ~92% |
| SQuAD v2 (accuracy bench) | ~19% |
| BFCL (function calling) | ~32% |

**Use ~47% as the realistic baseline for budget math, not 60–95%.** Even at a
conservative third of the headline, weekly/monthly spend drops and the effective
context window grows — but plan against the codebase-exploration figure.

## The risk that makes it opt-in

- **It intercepts every prompt.** headroom sits in the most sensitive position
  possible — between your editor and the API. Its data-egress posture is
  **UNDETERMINED**. Before enabling, verify and disable any phone-home: does
  `headroom wrap claude` send prompts or compressed summaries to upstream
  servers? Is the `Kompress-v2-base` model fetch one-time only? Are there
  offline-only / opt-out flags? Treat "no telemetry" as unproven until checked.
- **Pre-1.0, data-loss reports.** Compression can drop content; a bad compress
  on a code task can silently lose context. This is why it is not default-on.
- **Local model cost.** The HuggingFace compressor model runs locally — measure
  CPU/RAM during a compress. If too heavy, fall back to its deterministic
  compressors only (SmartCrusher for JSON, CodeCompressor for AST).
- **Don't enable `headroom learn`.** It competes with the rig's own
  `learnings/distilled.md` curation; compare side-by-side after 30 days, not before.

## Isolation

Install via **`pipx`**, never bare `pip`, so its transitive deps can't
contaminate the rig's hook scripts (`cost_tracker.py`, `mcp_trimmer.py`,
`dream_loop.py`):

```bash
pipx install "headroom-ai[all]"
```

## Evaluation recipe (the deferred user action)

1. **Drop-in (reversible):** `headroom wrap claude` on the laptop. Measure token
   savings on a real codebase-exploration session vs an unwrapped baseline.
2. **Acceptance gate (≥1 week):** savings ≥30% on codebase work AND zero
   phone-home verified. Only then add it to a daily workflow.
3. **MCP (if (1) proves out):** `headroom mcp install` exposes compress/retrieve
   as tools usable from any skill.
4. **Proxy (deferred):** the OpenAI-compatible HTTP proxy only if language-agnostic
   interception is needed.

Reversible by `unalias` + `pipx uninstall headroom-ai`. The
`enhancements/headroom/smoke-test.sh` checks the binary resolves after a manual install.

## See also

- `core/context-budget-policy.md` — native token reduction (try this first).
- `playbooks/token-economy/wrap-claude-code-with-headroom.md` — the wrap/MCP/proxy
  workflow + A/B methodology.
- `profiles/enhanced-tier2.yaml` — the opt-in profile that declares it.
