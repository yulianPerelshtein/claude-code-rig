---
name: verification-council
description: >-
  Dispatch divergent-mandate reviewers (evidence-verifier + adversarial, plus an
  optional decision red-team) at a consequential, about-to-propagate artifact, then
  synthesize and fix before propagation. Use for plans, schema-bearing docs,
  designs, and migrations whose patterns will be copied into other files.
allowed-tools: Task, Read, Grep, Glob, WebFetch
---

# Verification council

Operationalizes `playbooks/ai-assisted-coding/verification-council.md`. Run it
when an artifact is **consequential AND its patterns are about to propagate**
(a plan, a schema-bearing doc, a design, a migration) — not on trivial or
one-off changes (cost-gate it).

## Inputs

1. The **artifact** (a file path or pasted content).
2. A **claim list** — the load-bearing factual claims the artifact depends on
   (commands, schemas, API shapes, version facts). If the user didn't supply
   one, extract the candidate claims first and confirm.

## Procedure

Dispatch the reviewers **in parallel** (Task tool), each with a divergent
mandate. Keep them isolated — do not let one reviewer's framing leak into
another.

1. **Evidence-verifier** (read-only; `agent: code-reviewer` or
   `general-purpose` with `WebFetch`). For each claim, confirm it against an
   *authoritative external source* and **quote** the source. No "looks right" —
   a claim is either sourced-and-quoted or flagged UNVERIFIED.
2. **Adversarial reviewer** (read-only). Hunt internal contradictions, stale or
   legacy framing, broken cross-references, leaks, and blind spots. Do **not**
   re-litigate locked decisions — instead check they are applied *consistently*.
3. **(Optional) decision red-team** — include only if the user asks. May
   challenge a locked decision **only** with new *disconfirming evidence*;
   otherwise stay silent. Guards against false consensus without inviting churn.

## Synthesis gate

Collect findings and classify each: **blocker / should-fix / nice /
downstream**. Then:

1. **Fix every blocker in the artifact** before any copy-out.
2. Report the should-fix / nice / downstream items for the user to triage.
3. Only after blockers are fixed, propagate the (now-corrected) patterns.

Report format: a table of `finding | severity | source/evidence | fix applied?`
plus a one-line verdict (PROPAGATE / FIX-FIRST / BLOCKED).

## Worked example

The 2026-06-17 run on a rewritten `PACKAGE_STRUCTURE.md` caught three factual
errors (wrong marketplace command, non-`./` component paths, a structurally
invalid hooks manifest) plus two blockers — all fixed before the patterns were
propagated to four downstream docs. See the playbook for the full write-up.

## What it does NOT do

- Does not re-litigate locked decisions by default (red-team is opt-in,
  evidence-gated).
- Does not run on trivial changes — reserve it for consequential, propagating
  artifacts.
