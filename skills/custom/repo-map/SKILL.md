---
name: repo-map
description: >-
  Generate a ranked, token-budgeted orientation map of a repository — the most
  central functions/classes/types, signatures only — via tree-sitter tags +
  PageRank. Use when orienting in an unfamiliar or large codebase before broad
  investigation. Complements serena's on-demand symbol lookup; pass the task's
  files as focus for task-aware ranking.
allowed-tools: Bash, Read, Glob
---

# Repo map

A breadth-first **orientation** map: which definitions are most central to a
repo, ranked by a reference-graph PageRank, rendered as signatures only within a
token budget. Reproduces Aider's repo-map locally (tree-sitter + a self-contained
PageRank; no egress). It is the complement to serena — serena answers depth-first
"give me symbol X and its refs"; this gives the up-front *lay of the land*.

## When to use

- Landing in an **unfamiliar or large** repo and you need orientation fast.
- Before a broad investigation / parallel fan-out, to pick where to look.
- After a big change, to re-see what's central (pass `--focus` on touched files).

**Skip it** for a small or already-familiar repo, or when you need a specific
symbol's body — use serena or Read for that. This is orientation, not source.

## How to run

The tool ships next to this skill as `repo_map.py`. Locate it (plugin install vs
bespoke `~/.claude` install vs source checkout), then run it via `uv` so the
parsers are fetched on demand — no global install:

```bash
RM="$(ls "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/skills/custom/repo-map/repo_map.py" \
        "$HOME/.claude/skills/repo-map/repo_map.py" \
        "$HOME/claude-code-rig/skills/custom/repo-map/repo_map.py" 2>/dev/null | head -1)"
[ -z "$RM" ] && { echo "repo-map: repo_map.py not found (plugin/bespoke/source)" >&2; exit 1; }
uv run --with tree-sitter --with tree-sitter-python \
       --with tree-sitter-javascript --with tree-sitter-typescript \
       python "$RM" --root . --budget 1024
```

The **first** run fetches ~4 small wheels from PyPI (tree-sitter + the three
grammars), cached by `uv` thereafter; **no repository data is transmitted** —
analysis is fully local.

Make it **task-aware** by biasing the ranking toward the files in play — repeat
`--focus` for each (the current task's files, or ones the user named):

```bash
… python "$RM" --root . --focus path/to/a.py --focus path/to/b.ts
```

Flags: `--root` (default cwd / git top), `--budget` (approx tokens, default
1024), `--focus PATH` (repeatable; relative to where you run it), `--max-files`,
`--no-cache`. Languages: Python, JavaScript/JSX, TypeScript/TSX. Output is cached
on file mtime under `~/.claude/data/repo-map-cache/`, so re-runs are fast. Very
large repos are capped at `--max-files` (truncated by path order before ranking);
raise it if needed.

## How to read the output

- Files are listed **most-central first**; within a file, by line number.
- Each line is a definition's signature, indented under its file as
  `<line>: <signature>`.
- Higher placement = more referenced / closer to your focus — good first reading
  targets. Then dive into bodies with **serena** or **Read**.

## See also

- `playbooks/ai-assisted-coding/repo-map.md` — when/why and the workflow.
- `domains/memory/serena.md` — the depth-first counterpart.
- `playbooks/ai-assisted-coding/parallel-agent-fan-out.md` — use the map to scope
  what each agent investigates.
