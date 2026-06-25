# OTel / insights review

A periodic look at the quantitative telemetry so cost and efficiency trends are
visible, not anecdotal. The complement to the weekly (qualitative) retrospective.

## Prerequisite

Telemetry enabled on the machine you're reviewing — see
`domains/observability/claude-code-otel.md`. With no backend, `npx ccusage@latest`
gives a local rollup from the on-disk transcripts; in-session, `/cost` shows the
current session.

## Cadence

Monthly (or whenever a bill surprises you), ~10 minutes.

## What to look at

1. **Cache hit ratio** — `claude_code.token.usage` split by `type`. A healthy
   ratio of `cacheRead` to `input` means prompt caching is working; a drop means
   something is busting the cache (churning system prompt, reordered context).
2. **Cost by `query_source`** — main vs subagent vs auxiliary. If subagents
   dominate cost, revisit how often you fan out and whether `haiku` would do.
3. **Cost by `model`** — are expensive models being used for cheap mechanical
   work? Pin `model: haiku` on those skills/agents.
4. **Edit accept/reject** — `claude_code.code_edit_tool.decision`. A high reject
   rate signals prompts that produce edits you don't want — a prompt-optimization
   target.
5. **Active time vs session count** — sustained growth without matching output
   (commits/PRs/LoC) is a process-drag signal.

## Turn findings into action

- Cache busting → audit what changes between turns (see
  `domains/context-engineering/native-context-levers.md`).
- Wrong model for the job → right-size with `model:` frontmatter
  (`core/skill-frontmatter-reference.md`).
- High reject rate on a skill → run `/optimize-prompt` on it, then measure with
  `playbooks/prompt-optimization/ab-testing-skills.md`.

Record one or two concrete changes per review; this loop is for decisions, not
dashboards-for-their-own-sake.

> `/insights` may be available as a built-in summary in newer CLI versions; if
> present, use it as a starting point, but the metrics above are the
> doc-backed source of truth.

## See also

- `domains/observability/claude-code-otel.md` — setup + metric reference.
- `playbooks/continuous-improvement/weekly-retrospective.md` — the qualitative half.
