# Verification council (evidence + adversarial review)

A reusable orchestration pattern for **consequential artifacts whose patterns
are about to propagate** (a plan, a schema-bearing doc, a design, a migration).
Verifying at the propagation point is the cheapest place to catch a multiplying
error.

> The operational **skill** (`skills/custom/verification-council/SKILL.md`) that
> dispatches the reviewers ships in the rig; this playbook is the
> when/why/how it encodes.

## When to run

- The artifact is consequential AND its patterns will be copied into other
  files/phases.
- Not for trivial or one-off changes (cost-gate it).

## Roles (divergent mandates, run in parallel)

1. **Evidence-verifier** — must confirm load-bearing claims against
   *authoritative external sources* and **quote** them. No "looks right".
2. **Adversarial reviewer** — hunt internal contradictions, stale/legacy
   framing, broken cross-references, and blind spots. Do not re-litigate locked
   decisions; check that they're applied *consistently*.
3. **(Optional) decision red-team** — may challenge a locked decision **only**
   with new disconfirming evidence; otherwise stay silent. Guards against
   false-consensus without inviting churn.

## Gate

Synthesize findings → **correct the artifact** → *then* propagate. Classify
findings (blocker / should-fix / nice / downstream) and fix blockers before any
copy-out.

## Worked example (2026-06-17)

Run on a rewritten `PACKAGE_STRUCTURE.md`: the evidence-verifier caught three
factual errors (wrong marketplace command, non-`./` component paths, a
structurally invalid hooks manifest) and the adversarial reviewer caught two
blockers — all fixed before the patterns were propagated to four downstream
docs.

Related: `playbooks/code-review/ai-review-skepticism.md`,
`playbooks/ai-assisted-coding/parallel-agent-fan-out.md`.
