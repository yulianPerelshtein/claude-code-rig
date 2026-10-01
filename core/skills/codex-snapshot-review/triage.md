# Triage of reviewer findings

The reviewer's severity is a proposal. Nothing reaches the user until it has
been reproduced, and a finding that cannot be reproduced is reported as such,
not as a defect.

## Per finding

1. **Read** the code at `file:line` in the snapshot worktree, not in the user's
   checkout (it may have moved on).
2. **Reproduce.** Run the reviewer's evidence command, or write a probe in the
   session scratchpad that imports the snapshot's code. Never write into the
   snapshot or the user's checkout.
3. **Check reach yourself.** Follow `reachable_from` to a real entry point, or
   search for one. Missing routes, writers or data make it latent. Where the
   question is "does this input exist", count it on real data when you can, and
   give the number.
4. **Check design intent.** Read what `why_not_by_design` cites, then what it
   did not: the package docs, the plan's decisions, the tests that pin the
   behaviour, the review history of the code.
5. **Classify** it as one of:

   | Class | Meaning |
   | --- | --- |
   | current defect | wrong today, on a reachable path |
   | latent defect | wrong in code, but no input reaches it today |
   | incomplete answer | an earlier review request was only partly met |
   | pre-existing | the base has it too; not this change's |
   | future contract choice | a design question for a later change |
   | integration hazard | breaks a branch above in the stack, or a merge |
   | by design | a document or test states the behaviour on purpose |
   | wording | a claim in the PR body or docs is wrong; the code is fine |
   | not reproduced | the evidence does not hold |

6. **Decide**: keep, downgrade, reword or drop, with a one-line reason. When the
   reviewer's fix goes the wrong way, say so and give the right one.

## Severity after triage

- BLOCKER: reproduced, reachable, and wrong output or a crash on that path.
- SHOULD-FIX: reproduced but latent, or reachable with a small effect.
- Latent findings carry the reach number ("0 of N members on seven models") so
  the user can decline them with evidence.
- By design, pre-existing and not reproduced findings are listed, not counted.

## Table

`review_snapshot.py table` fills the first three columns. Fill the rest:

| Id | Finding (Codex severity -> ours) | Reach | Reproduced? | How | Assessment | Proposed answer |
| --- | --- | --- | --- | --- | --- | --- |

- **Reproduced?** Yes, No, or Partly, then the fact that decided it.
- **How**: the probe or command and its result, short enough to re-run.
- **Assessment**: the class above, plus reach in numbers where you have them.
- **Proposed answer**: the fix and its test, a reply that declines with the
  numbers, a PR body edit, or "user's call: (a) ... (b) ...".

End with one line: findings reported, kept, downgraded, dropped as by design or
unreachable. Over several reviews that line shows whether the prompt's rating
rules work.
