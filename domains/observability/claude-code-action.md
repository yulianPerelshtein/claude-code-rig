# claude-code-action (Claude in CI) — Tier 2, opt-in

[anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)
(MIT, ~8k★, v1.0) is the **official** GitHub Action for running Claude Code in
CI — PR reviews, `@claude` mentions on issues/PRs, and scheduled tasks. Opt-in in
this rig (`profiles/enhanced-tier2.yaml`); the workflow ships at
`.github/workflows/claude-code.yml`.

## Read this first: it BILLS your API account

The Session-1 note that it's "free for Team subscribers in CI" is **false**
(`SOTA_REFRESH.md §4.5`). The action authenticates via an **API key / Bedrock /
Vertex / Foundry credential on your runner and bills that API account** per
token. The README does **not** advertise Pro/Max/Team subscription OAuth in CI —
treat "free for subscribers" as unverified/false. Budget metered API spend before
enabling.

## How the rig ships it (safely gated)

`.github/workflows/claude-code.yml` is deliberately **not** triggered on `push`
or on every PR. It runs only:

- **`workflow_dispatch`** — you manually trigger it, or
- **`issue_comment` / PR review comment containing `@claude`** — explicit invocation.

And the job is guarded so it **no-ops when `ANTHROPIC_API_KEY` is absent** —
installing the workflow file costs nothing and bills nothing until you add the
secret and explicitly invoke it. This keeps the rig's other CI workflows
unaffected and prevents accidental spend.

## Enabling it (deferred user action)

1. Add an `ANTHROPIC_API_KEY` repo secret (or Bedrock/Vertex creds + the matching
   `use_bedrock`/`use_vertex` inputs).
2. Decide the budget — every `@claude` invocation and scheduled run bills tokens.
3. Invoke via `@claude` in a PR/issue comment, or `workflow_dispatch`.
4. Optionally narrow `allowed_tools` / add a turn cap in the workflow inputs to
   bound cost per run.

## When it's worth it

- Automated first-pass PR review on a shared repo.
- `@claude fix this`-style triage on issues.
- Scheduled maintenance (dependency notes, changelog drafts).

For a solo personal rig, the interactive CLI is usually cheaper than CI billing —
enable this when collaboration or automation justifies the metered spend.

## See also

- `.github/workflows/claude-code.yml` — the gated workflow.
- `playbooks/ci/claude-in-ci.md` — setup, cost control, and invocation patterns.
- `profiles/enhanced-tier2.yaml` — the opt-in profile.
