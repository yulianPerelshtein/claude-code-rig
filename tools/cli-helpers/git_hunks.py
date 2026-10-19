#!/usr/bin/env python3
"""
List and stage single diff hunks without an interactive prompt.

`git add -p` needs a terminal, so an agent splitting one change into commits that each stand alone cannot use it.
`list` numbers the unstaged hunks of each changed file; `stage` puts the chosen hunks of one file in the index with
`git apply --cached`, leaving the rest in the working tree. Numbers come from a `list` run just before: staging
renumbers what is left.

    git_hunks.py list [PATH ...]          # "<path> <n>: @@ -a,b +c,d @@ <first changed line>"
    git_hunks.py stage PATH N [N ...]     # stage hunks N of PATH, numbered as `list PATH` shows them
"""
import argparse
import subprocess
import sys
from typing import List, Sequence, Tuple


def _git(*args: str, stdin: str = "") -> str:
    """Run git in the current repository and return its stdout; a failing git command raises."""
    return subprocess.run(["git", *args], input=stdin or None, check=True, capture_output=True, text=True).stdout


def split_hunks(diff: str) -> Tuple[str, List[str]]:
    """
    Split a one-file unified diff into its file header and its hunks.

    Parameters
    ----------
    diff : str
        `git diff` output for one path.

    Returns
    -------
    Tuple[str, List[str]]
        The header lines (`diff --git`, `index`, `---`, `+++`) and each hunk's text from its `@@` line to the next.
    """
    header: List[str] = []
    hunks: List[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("@@"):
            hunks.append(line)
        elif hunks:
            hunks[-1] += line
        else:
            header.append(line)
    return "".join(header), hunks


def _file_diff(path: str) -> str:
    """The unstaged diff of one path, three lines of context, no colour or external driver."""
    return _git("diff", "--no-color", "--no-ext-diff", "-U3", "--", path)


def list_hunks(paths: Sequence[str]) -> List[str]:
    """One line per unstaged hunk of `paths` (every changed file when empty), numbered from 1 per file."""
    lines = []
    for path in paths or _git("diff", "--name-only").splitlines():
        _, hunks = split_hunks(_file_diff(path))
        for number, hunk in enumerate(hunks, 1):
            rows = hunk.splitlines()
            first = next((row for row in rows[1:] if row[:1] in "+-"), "")
            lines.append(f"{path} {number}: {rows[0]} {first[:80]}")
    return lines


def stage(path: str, numbers: Sequence[int]) -> None:
    """
    Stage the chosen hunks of one path.

    Parameters
    ----------
    path : str
        A tracked file with unstaged changes.
    numbers : sequence of int
        Hunk numbers as `list_hunks([path])` shows them.

    Raises
    ------
    SystemExit
        When a number names no hunk; nothing is staged then.
    """
    header, hunks = split_hunks(_file_diff(path))
    unknown = sorted(n for n in set(numbers) if not 1 <= n <= len(hunks))
    if unknown:
        raise SystemExit(f"{path} has {len(hunks)} hunk(s); no hunk {unknown}")
    patch = header + "".join(hunks[n - 1] for n in sorted(set(numbers)))
    _git("apply", "--cached", "--recount", "-", stdin=patch)


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("list").add_argument("paths", nargs="*")
    stage_cmd = sub.add_parser("stage")
    stage_cmd.add_argument("path")
    stage_cmd.add_argument("numbers", nargs="+", type=int)
    args = ap.parse_args(argv)
    if args.command == "list":
        print("\n".join(list_hunks(args.paths)))
    else:
        stage(args.path, args.numbers)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
