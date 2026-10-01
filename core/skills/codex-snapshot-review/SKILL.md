---
name: codex-snapshot-review
description: Run a read-only Codex review of a pinned snapshot (a pushed branch, a PR in a stack, or uncommitted work), get its findings as schema-checked JSON, and reproduce each finding before it reaches the user. Use when asked for a Codex review, an outside or adversarial review pass, or a council review of a change.
argument-hint: "<name> (--ref <ref> --base <ref> | --working-tree)"
---

# Codex snapshot review

Codex reviews a frozen copy of the change in its own worktree and answers in
JSON that matches `findings.schema.json`. Claude then reproduces every finding
and re-rates it. Codex never edits, commits, pushes or posts.

This skill adds an outside reviewer. It replaces no review the project already
runs (its own review skill, critics or standards). For a quick look at the live
branch, the Codex plugin's `/codex:review` and `/codex:adversarial-review` are
enough; they cannot pin a commit.

Files beside this one: `review_snapshot.py` (snapshot, cleanup, triage table),
`prompt-template.md`, `findings.schema.json`, `triage.md`.

## 1. Pin the change

```bash
RS="${CLAUDE_SKILL_DIR}/review_snapshot.py"
git fetch origin                                  # for pushed refs
python3 "$RS" create <name> --ref origin/<branch> --base origin/<target>
python3 "$RS" create <name> --working-tree [--path <p> ...]   # uncommitted work
```

Run it from inside the repository. Add `--link .venv` (repeatable) to symlink a
path of the main checkout, such as a virtualenv, into the snapshot. The output
is JSON: `worktree`, `head`, `base` (already the merge base), and the refs
`refs/review/<name>/{head,base}`.

- The worktree is at `~/.claude-worktrees/<project>/review-<name>` (`--root`
  moves it). Keep it on disk: `/tmp` is often a RAM-backed tmpfs.
- It holds tracked files and the snapshot only. Git hooks are off while it is
  added, so a hook that copies `.env` or local settings into new worktrees does
  not run. Ignored files never enter a working-tree snapshot.
- The working-tree mode builds its tree in a temporary index: the user's
  index, staged state and files do not move.

## 2. Write the prompt

Copy `prompt-template.md`'s block to the session scratchpad as
`<name>.prompt.md` and fill every slot. One prompt per change.

Project lens: if the skill list shows a `<project>-review-lens` skill for this
repository, load it and paste its checklist into `{{LENS}}`. Otherwise drop the
section.

## 3. Run Codex, read-only, in the background

```bash
codex exec -s read-only --ephemeral -C <worktree> \
  --output-schema "${CLAUDE_SKILL_DIR}/findings.schema.json" \
  -o <scratchpad>/<name>.json - < <scratchpad>/<name>.prompt.md \
  > <scratchpad>/<name>.log 2>&1
```

- Start each review with the Bash tool's `run_in_background`; several can run
  in parallel (five took 30-40 minutes). The harness reports each exit, so do
  not poll. A `pgrep -f "codex exec"` waiter matches its own command line and
  never ends.
- After the exit, check that `<name>.json` exists and parses. If not, read the
  tail of the log.
- Always `-s read-only`. Never `workspace-write`, `--full-auto`,
  `--approve-for-me`, a `--dangerously-*` flag, `--add-dir`, or the Codex
  plugin's rescue or task path.

## 4. Triage

```bash
python3 "$RS" table <scratchpad>/<name>.json [...] > <scratchpad>/triage.md
```

The table numbers the findings `<name>-<n>`, fills the finding and reach
columns, and flags any finding that breaks the rating rules (a BLOCKER that is
not reachable, a finding with no evidence). Fill the other columns by following
`triage.md`. Give the user only the triaged table: reproduced findings,
re-rated, each with a proposed answer.

## 5. Clean up

```bash
python3 "$RS" remove <name>
```

It removes the worktree and both refs. A snapshot with edits in it is kept,
refs included, so you can see what changed; find out why before you remove it
by hand.

## Stacked pull requests

- Pin each layer against the layer below it (`--base origin/<parent branch>`),
  one snapshot and one prompt per layer, so a review never reads the stack's
  other changes.
- A fix belongs on the lowest layer that owns the code, then travels up the
  stack the way that stack already moves: a rebase for a stack managed by a
  stacking tool, merge-up for a stack that has merged up before. Do not mix the
  two in one stack.
- Before you keep a finding on a layer, check that a fix in a lower layer has
  not already reached it: `git merge-base --is-ancestor <fix> <layer head>`.
- Every push, force-push, PR edit and PR comment is the user's call.
