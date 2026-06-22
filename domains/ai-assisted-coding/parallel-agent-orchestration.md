# Parallel-agent orchestration

Patterns for running many coding/analysis agents at once.

## Independence + incremental writes

- Spawn agents **fully independent** — no cross-agent communication. The main
  session synthesizes after all return.
- Each agent: read its target → **write its output file after the first 2–3
  steps**, then append as it discovers more → return a one-paragraph summary.
- The end-buffering failure: if an agent buffers findings until the end, a
  timeout (laptop sleep, network drop) loses everything. The fix is incremental
  writes, **not** a tool-call cap (that was a wrong diagnosis).

## Sizing

- Repos under ~2000 files work as single-agent passes.
- Larger repos need **hub-and-spoke**: a cartographer agent plus
  API / data / patterns / testing agents.

## Avoiding shallow analysis

Agents reliably read README, routes/controllers, models/schemas, manifests,
compose files. They reliably miss the **primary service/business-logic file**,
utility modules, test edge cases, and migration history. Name the service file
explicitly in the prompt; for deep passes: service file → utils → 3 test files
→ last 3 migrations.

Companion playbook: `playbooks/ai-assisted-coding/parallel-agent-fan-out.md`.
