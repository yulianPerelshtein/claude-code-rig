# Weekly Coach review

If you've adopted AI-Engineering-Coach (Tier 2, opt-in — see
`domains/observability/ai-engineering-coach.md`), this is the weekly ritual that
turns its forensic dashboard into actual rig improvements. Skip this playbook if
the Coach isn't installed; the native OTel review
(`playbooks/observability/otel-insights-review.md`) covers the quantitative side
regardless.

## Prerequisite

The Coach `.vsix` built from source and installed in VS Code, rendering your
Claude Code sessions on WSL2 (deferred user action — no prebuilt release exists).

## Cadence

Weekly, ~10 minutes. Pairs with the weekly retrospective
(`playbooks/continuous-improvement/weekly-retrospective.md`).

## What to look at

1. **Code-review findings** — the most rig-relevant of the ~45 rules. Recurring
   anti-patterns here are candidates for a `code-reviewer` agent-memory note or a
   new `domains/software-design/clean-code.md` rule.
2. **Skill Finder** — it mines repeated prompts and suggests skill candidates. A
   repeated multi-step prompt is a skill: draft it
   (`core/skill-frontmatter-reference.md`), and feed the suggestion into the same
   pipeline as a dream-report candidate.
3. **Session hygiene + context management** — flags long, unfocused sessions or
   context bloat; cross-check against `core/context-budget-policy.md`.
4. **Prompt quality** — low-scoring prompts are `/optimize-prompt` targets
   (`playbooks/prompt-optimization/prompt-checklist.md`).

## Turn findings into action

- A Skill Finder candidate → author the skill, measure it with
  `playbooks/prompt-optimization/ab-testing-skills.md`.
- A recurring code-review anti-pattern → one-line rule in `learnings/distilled.md`
  (or `domains/software-design/clean-code.md` if universal).
- A context-management flag → confirm against the OTel cache-hit trend.

Record one or two concrete changes per review — the Coach is an input to the
improvement loop, not a dashboard to admire.

## See also

- `domains/observability/ai-engineering-coach.md` — the evaluation + caveats.
- `playbooks/continuous-improvement/weekly-retrospective.md` — the broader loop.
- `playbooks/observability/otel-insights-review.md` — the quantitative half.
