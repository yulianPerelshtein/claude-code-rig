---
name: monthly-drift
description: Diff the deployed ~/.claude against the rig and flag config/hook drift + stale extension pins (report-only).
argument-hint: "--target <repo> [--routine-mode]"
allowed-tools: Bash, Read, Grep
---

# /monthly-drift  (outcome: report-only)

Operate on `--target` (default = the rig repo). Surface where the deployed
config has drifted from the rig and where pinned extensions are stale.

**Scope note — read before running.** Whether the rig's own files match what is
deployed is now asserted mechanically by the `self-check` routine
(`deployed-matches-committed` compares every file in the running plugin against
the commit it claims, and `delivery-paths-agree` catches plugin/checkout skew).
Do not re-derive that here by hand; a model diffing trees is slower and less
reliable than the hash comparison already running weekly. This routine covers
what `self-check` cannot: **upstream** staleness, which needs the network.

1. **Stale pins (the core of this routine).** Compare pinned commits/versions in
   `<target>/manifests/marketplace.yaml` against upstream (`git ls-remote` /
   release tags); flag stale extensions and available plugin updates.
2. **Deployed config**, but only the parts that exist on this install:
   `~/.claude/settings.json` against `<target>/core/settings.template.json`.
   Report what is present rather than assuming — on a plugin install
   `~/.claude/hooks/` and most of `~/.claude/skills/` do not exist at all (hooks
   run from the plugin cache), so diffing them silently compares nothing. If a
   path is absent, say it is absent; do not report "no drift".
3. Write a report to `~/.claude/routine-reports/<date>-drift.md` (the runner
   supplies the path under report-only; do not modify the repo).
4. You MAY propose a **mechanical** pin-bump diff only — never auto-apply a
   judgement edit.

This routine cross-references the manual
`playbooks/continuous-improvement/monthly-drift-check.md`; it automates that
check, it does not duplicate its prose. Never modify source `~/.claude`
originals; never merge; never push to a default branch.
