---
name: monthly-drift
description: Diff the deployed ~/.claude against the rig and flag config/hook drift + stale extension pins (report-only).
argument-hint: "--target <repo> [--routine-mode]"
allowed-tools: Bash, Read, Grep
---

# /monthly-drift  (outcome: report-only)

Operate on `--target` (default = the rig repo). Surface where the deployed
config has drifted from the rig and where pinned extensions are stale.

1. Diff deployed `~/.claude/{settings.json,hooks,skills}` against `<target>`
   (read-only — never modify the deployed originals).
2. Compare pinned commits/versions in `<target>/manifests/marketplace.yaml`
   against upstream (`git ls-remote` / release tags); flag stale extensions and
   available plugin updates.
3. Write a report to `~/.claude/routine-reports/<date>-drift.md` (the runner
   supplies the path under report-only; do not modify the repo).
4. You MAY propose a **mechanical** pin-bump diff only — never auto-apply a
   judgement edit.

This routine cross-references the manual
`playbooks/continuous-improvement/monthly-drift-check.md`; it automates that
check, it does not duplicate its prose. Never modify source `~/.claude`
originals; never merge; never push to a default branch.
