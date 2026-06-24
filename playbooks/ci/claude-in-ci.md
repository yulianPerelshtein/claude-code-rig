# Claude in CI (claude-code-action)

Setup, cost control, and invocation patterns for the **opt-in** official
Claude-in-CI action. Read `domains/observability/claude-code-action.md` first —
the key fact is that it **bills your API account**, not a subscription.

## The cost model (don't skip this)

Every invocation — an `@claude` comment, a scheduled run, a PR-review trigger —
runs Claude Code on the runner against an **API key / Bedrock / Vertex / Foundry**
credential and **bills that account per token**. There is no subscription-free CI
path. Treat CI runs as metered spend and bound them.

## How the rig's workflow is gated

`.github/workflows/claude-code.yml` ships **safe by default**:

- Triggers: **`workflow_dispatch`** (manual) and **`@claude` mentions** in
  issue/PR comments. **Never `on: push`** and never on every PR open.
- The job **no-ops when `ANTHROPIC_API_KEY` is unset** — the file can live in the
  repo indefinitely costing nothing, and it won't show as a failing check.
- This keeps it off the rig's standard 4-workflow green path until you opt in.

## Enabling (deferred user action)

1. Add the `ANTHROPIC_API_KEY` repo secret (or Bedrock/Vertex creds + the
   matching `use_bedrock: true` / `use_vertex: true` inputs).
2. Set a budget expectation and tell whoever shares the repo.
3. Bound per-run cost: narrow `claude_args` / `allowed_tools` and set a turn cap.
4. Invoke: comment `@claude <request>` on a PR/issue, or run the workflow
   manually from the Actions tab.

## Good uses vs. not

| Worth the spend | Skip it |
|---|---|
| First-pass PR review on a shared repo | Solo repo where the CLI is cheaper |
| `@claude fix this` issue triage | Anything you'd do faster interactively |
| Scheduled changelog / dependency notes | High-frequency triggers (cost compounds) |

## Cost-control checklist

- [ ] Workflow triggers limited to manual + `@claude` (no `push`).
- [ ] Turn/`max_turns` cap set.
- [ ] `allowed_tools` scoped to what the task needs.
- [ ] Spend monitored (the same API account shows in `npx ccusage` / OTel
      `claude_code.cost.usage` if you also run the CLI on that key).

## See also

- `domains/observability/claude-code-action.md` — evaluation + billing facts.
- `.github/workflows/claude-code.yml` — the gated workflow definition.
- `core/authored-content-rules.md` — keep any AI-authored PR/issue content
  within the rig's content rules.
