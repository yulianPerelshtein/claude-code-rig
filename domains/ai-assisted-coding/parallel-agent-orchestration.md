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

## A read-only brief is not a fence

Review agents briefed read-only, with a `tools:` list like `Bash(git *)`, still
ran `sed -i`, stashed, switched branches and committed in checkouts they could
reach. A fork started with the Agent tool (`subagent_type: fork`) inherits the
parent's conversation, pending plan included, and may carry that plan out. The
permission classifier blocks some of these writes, not all.

- Before launch: snapshot every reachable checkout (`git status --porcelain`,
  `git diff | sha256sum`, `git stash list`) and touch a marker file. Name the
  write steps as out of scope ("report and stop; do not edit, commit, or write
  memory").
- The report is complete before the agent starts writing: TaskStop it when the
  report arrives. Never commit while it still runs, and deny a permission prompt
  that names its target directory.
- Audit only after it stops: compare with the snapshot, plus
  `find <tree> -newer <marker>`, which also sees untracked and gitignored files.
- For review work, a `general-purpose` agent with an explicit read-only paragraph
  made no write attempts where custom critic agents did.
- Such a fork cannot call the Agent tool. Launch parallel forks from the
  top-level session, in one message.

## Brief a reviewer with the artifact, not your conclusions

A review agent given the author's intent, plan reading or trade-offs confirms
them; given only the diff and the spec, it judges them. Per-step critic runs
briefed with the author's conclusions missed three gaps that the same agents
found once they judged the final diff against the PR body's claims.

- Hand over the diff (or a frozen snapshot worktree), the ticket and the docs
  the change claims to satisfy. Leave out your hypothesis, your reading of the
  plan and the trade-offs you already settled.
- Ask a design reviewer to test every claim in the PR body against the diff,
  "behaviour unchanged" included, and to name work the change does that
  nothing reads.
- Ask a test reviewer to state, for each suggestion it drops, the end-to-end
  failure that test would have caught. A dropped suggestion with a real
  scenario is a should-fix, whatever unit coverage exists elsewhere;
  `domains/testing-tdd/test-economy.md` asks the same question of every test.

Companion playbook: `playbooks/ai-assisted-coding/parallel-agent-fan-out.md`.
