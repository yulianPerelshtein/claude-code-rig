# Evaluation frameworks for AI features

How to answer "How will we know this AI system is working?" — the dimensions,
rubrics, tooling, dataset, and guardrails that the `eval-planner` and
`eval-auditor` agents and the `eval-spec` skill build on. Adapted from the GSD
eval references (MIT).

## Eval dimensions by system type

Pick the dimensions that match what you're building; always include **safety**
(user-facing) and **task completion** (agentic).

| System type | Core dimensions |
|---|---|
| RAG | context faithfulness, hallucination rate, answer relevance, retrieval precision/recall, source citation |
| Multi-agent | task decomposition, inter-agent handoff, goal completion, loop detection |
| Conversational | tone/style, safety, instruction following, escalation accuracy |
| Extraction | schema compliance, field accuracy, format validity |
| Autonomous | safety guardrails, tool-use correctness, cost/token adherence, task completion |
| Content | factual accuracy, brand voice, tone, originality |
| Code | correctness, safety, test pass rate, instruction following |

## Rubric format

Each dimension gets a concrete, domain-specific rubric — not a generic label:

> **PASS:** {specific acceptable behavior in domain language}
> **FAIL:** {specific unacceptable behavior in domain language}
> **Measurement:** Code | LLM judge | Human
> **Priority:** Critical | High | Medium

Measurement approaches:

- **Code-based** — schema validation, required-field presence, performance
  thresholds, regex/format checks. Deterministic; put in CI.
- **LLM judge** — tone, reasoning quality, safety-violation detection. Requires
  calibration against human labels; split the parser from the call so the parse
  is unit-testable (the AI-as-judge testing discipline).
- **Human review** — edge cases, judge calibration, high-stakes sampling.

## Tooling defaults

Detect existing tools first (`grep` for `langfuse|langsmith|arize|phoenix|braintrust|promptfoo|ragas`).
If none, sensible open-source defaults:

| Concern | Default |
|---|---|
| Tracing / observability | Arize Phoenix (OpenTelemetry, self-hostable) |
| RAG metrics | RAGAS (faithfulness, relevance, context precision/recall) |
| Prompt regression / CI | Promptfoo (CLI-first, no account) |
| LangChain/LangGraph stack | LangSmith (overrides Phoenix if already in that ecosystem) |

## Reference dataset

- **Size:** 10 examples minimum; 20+ for production.
- **Composition:** critical paths, edge cases, known failure modes, adversarial
  inputs.
- **Labeling:** domain expert, or LLM judge with human calibration, or automated.
- **Timeline:** start building it during implementation, not after.

## Guardrails

For each critical failure mode, classify:

- **Online guardrail** (catastrophic) — runs on every request, real-time, must
  be fast. Keep minimal; each adds latency.
- **Offline flywheel** (quality signal) — sampled batch, feeds the improvement
  loop.

## Scoring (for an audit)

```text
coverage_score = covered_dimensions / total_dimensions * 100
infra_score    = (tooling + dataset + cicd + guardrails + tracing) / 5 * 100
overall_score  = coverage_score * 0.6 + infra_score * 0.4
```

Verdict bands: 80–100 production-ready (deploy with monitoring); 60–79 needs
work (fix critical gaps first); 40–59 significant gaps (do not deploy); 0–39 not
implemented.

A dimension is **COVERED** only if an implementation exists, targets the rubric
behavior, and runs (automated or documented manual). **PARTIAL** = exists but
incomplete; **MISSING** = no implementation. Don't credit documentation or
metric-logging as evaluation unless the metric drives a decision.
