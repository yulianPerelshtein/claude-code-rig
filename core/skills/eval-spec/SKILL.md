---
name: eval-spec
description: Scaffold or audit an AI feature's evaluation strategy (AI-SPEC.md / EVAL-REVIEW.md)
disable-model-invocation: true
argument-hint: "[plan|audit]"
---

Scaffold or audit the evaluation strategy for an AI/LLM feature. Reference:
`domains/ai-assisted-coding/eval-frameworks.md`.

Pick the mode from `$ARGUMENTS` (default `plan`):

- **plan** — delegate to the `eval-planner` agent: identify failure modes,
  select eval dimensions with concrete rubrics + measurement approaches, choose
  tooling (detect existing first, else Phoenix / RAGAS / Promptfoo / LangSmith),
  specify the reference dataset, design online/offline guardrails, and write the
  Evaluation Strategy / Guardrails / Production Monitoring sections of
  `AI-SPEC.md`.

- **audit** — delegate to the `eval-auditor` agent: scan the implementation
  against `AI-SPEC.md`, score each dimension COVERED/PARTIAL/MISSING, audit the
  5 infrastructure components, compute the coverage/infra/overall scores and a
  verdict, and write `EVAL-REVIEW.md`.

Steps:

1. Determine the mode (`plan` or `audit`) from `$ARGUMENTS`.
2. Confirm the system type and the spec path if not obvious from the repo.
3. Invoke the matching agent with that context.
4. Report the file written and a one-line summary (dimensions planned, or the
   audit verdict + score).
