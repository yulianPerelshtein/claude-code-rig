#!/usr/bin/env python3
"""Pin a change for an outside reviewer, and turn its report into a triage table.

  create NAME --ref REF --base REF       pin a committed change (diff = BASE...REF)
  create NAME --working-tree [--path P]  pin uncommitted work on top of HEAD
  remove NAME                            remove the worktree, then the refs
  table REPORT.json [...]                markdown triage table from findings JSON

A snapshot is two refs, refs/review/NAME/{head,base}, plus a detached worktree at
ROOT/<project>/review-NAME. The refs are not tags, so `git push --tags` never
sends them. The working-tree mode builds its tree in a temporary index, so the
user's index and working tree are never touched. Run from inside the repository.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude-worktrees"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SEVERITIES = ("BLOCKER", "SHOULD-FIX", "NIT", "QUESTION")


class SnapshotError(Exception):
    """A precondition failed; the message is shown to the user as is."""


def git(*args: str, cwd: Path, env: dict | None = None) -> str:
    """Run git and return stdout without the trailing newline; raise on failure."""
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SnapshotError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.rstrip("\n")


def main_checkout(cwd: Path) -> Path:
    """Return the main checkout of the repository that contains cwd."""
    common = Path(
        git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)
    )
    return common.parent if common.name == ".git" else common


def ref_names(name: str) -> tuple[str, str]:
    """Return the head and base ref names for a snapshot name; reject unsafe names."""
    if not NAME_RE.match(name) or ".." in name or name.endswith((".lock", ".")):
        raise SnapshotError(f"bad snapshot name {name!r}: use letters, digits, . _ -")
    return f"refs/review/{name}/head", f"refs/review/{name}/base"


def worktree_path(root: Path, repo: Path, name: str) -> Path:
    """Return where the snapshot worktree of `name` lives."""
    return root / main_checkout(repo).name / f"review-{name}"


def ref_exists(ref: str, repo: Path) -> bool:
    """Return True when `ref` resolves in the repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref], cwd=repo, capture_output=True
    )
    return result.returncode == 0


def pin_ref(ref: str, base: str, repo: Path) -> tuple[str, str]:
    """Return (head, merge base) for a committed change, so base..head is BASE...REF."""
    head = git("rev-parse", "--verify", f"{ref}^{{commit}}", cwd=repo)
    base_commit = git("rev-parse", "--verify", f"{base}^{{commit}}", cwd=repo)
    return head, git("merge-base", base_commit, head, cwd=repo)


def pin_working_tree(name: str, paths: list[str], repo: Path) -> tuple[str, str]:
    """Commit the working tree (or `paths` of it) on HEAD through a temporary index."""
    base = git("rev-parse", "--verify", "HEAD^{commit}", cwd=repo)
    with tempfile.TemporaryDirectory() as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(scratch) / "index")}
        git("read-tree", "HEAD", cwd=repo, env=env)
        git("add", "--all", "--", *(paths or ["."]), cwd=repo, env=env)
        tree = git("write-tree", cwd=repo, env=env)
    if tree == git("rev-parse", "HEAD^{tree}", cwd=repo):
        raise SnapshotError("nothing to review: the working tree matches HEAD")
    message = f"review snapshot {name}"
    head = git("commit-tree", tree, "-p", base, "-m", message, cwd=repo)
    return head, base


def link_sources(links: list[str], repo: Path) -> list[Path]:
    """Resolve each --link path in the main checkout; raise if one is missing."""
    source_root = main_checkout(repo)
    for rel in links:
        if not (source_root / rel).exists():
            raise SnapshotError(f"--link {rel}: {source_root / rel} does not exist")
    return [source_root / rel for rel in links]


def link_into(worktree: Path, links: list[str], sources: list[Path]) -> None:
    """Symlink each source (e.g. a virtualenv) into the worktree at its own path."""
    for rel, source in zip(links, sources):
        target = worktree / rel
        if target.exists() or target.is_symlink():
            raise SnapshotError(f"--link {rel}: {target} already exists in the tree")
        target.symlink_to(source)


def create(args: argparse.Namespace, repo: Path) -> dict:
    """Pin the change, write the refs, add the detached worktree; return its facts.

    The worktree is added with git hooks off, so a hook that seeds new worktrees
    (a copied `.env`, local settings) cannot hand them to the reviewer. Anything
    that fails after the refs are written rolls the snapshot back.
    """
    head_ref, base_ref = ref_names(args.name)
    path = worktree_path(args.root, repo, args.name)
    if ref_exists(head_ref, repo) or path.exists():
        raise SnapshotError(f"snapshot {args.name!r} exists; remove it first")
    sources = link_sources(args.link, repo)
    if args.working_tree:
        head, base = pin_working_tree(args.name, args.path, repo)
    else:
        head, base = pin_ref(args.ref, args.base, repo)
    try:
        git("update-ref", head_ref, head, cwd=repo)
        git("update-ref", base_ref, base, cwd=repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        git("-c", "core.hooksPath=/dev/null", "worktree", "add", "--detach",
            str(path), head, cwd=repo)
        link_into(path, args.link, sources)
    except SnapshotError:
        remove(argparse.Namespace(name=args.name, root=args.root), repo)
        raise
    return {"name": args.name, "worktree": str(path), "head": head, "base": base,
            "head_ref": head_ref, "base_ref": base_ref}


def unlink_untracked_symlinks(worktree: Path) -> None:
    """Remove the links `create` added, so an unignored link does not block removal."""
    status = git("status", "--porcelain", "--untracked-files=normal", cwd=worktree)
    for line in status.splitlines():
        if line.startswith("?? "):
            entry = worktree / line[3:].rstrip("/")
            if entry.is_symlink():
                entry.unlink()


def remove(args: argparse.Namespace, repo: Path) -> dict:
    """Remove a clean snapshot worktree, then its refs; a dirty one keeps both."""
    head_ref, base_ref = ref_names(args.name)
    path = worktree_path(args.root, repo, args.name)
    if path.exists():
        unlink_untracked_symlinks(path)
        git("worktree", "remove", str(path), cwd=repo)
    for ref in (head_ref, base_ref):
        if ref_exists(ref, repo):
            git("update-ref", "-d", ref, cwd=repo)
    return {"name": args.name, "removed": str(path)}


def cell(text: object) -> str:
    """Make a value safe for one markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def report_lines(name: str, report: dict) -> list[str]:
    """Render one report: verdict, rows, flags, then the sound and open items."""
    lines = [f"### {name}: {report['verdict']}", "", cell(report["summary"]), "",
             "| Id | Finding (Codex severity -> ours) | Reach | Reproduced? | How "
             "| Assessment | Proposed answer |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    flags: list[str] = []
    for number, finding in enumerate(report["findings"], start=1):
        ident = f"{name}-{number}"
        where = finding["file"] + (f":{finding['line']}" if finding["line"] else "")
        lines.append(
            f"| {ident} | `{cell(where)}` {cell(finding['claim'])} "
            f"({finding['severity']} -> ?) | {finding['reach']}: "
            f"{cell(finding['reachable_from'])} |  |  |  |  |"
        )
        flags.extend(f"{ident}: {flag}" for flag in finding_flags(finding))
    lines += ["", "Flags for triage:" if flags else "Flags for triage: none"]
    lines += [f"- {flag}" for flag in flags]
    for title, key in (("Checked and sound:", "checked_and_sound"),
                       ("Not checked:", "not_checked")):
        lines += ["", title] + [f"- {cell(item)}" for item in report[key]]
    return lines + [""]


def finding_flags(finding: dict) -> list[str]:
    """Return the ways a finding breaks the rating rules of the review prompt."""
    flags = []
    if finding["severity"] not in SEVERITIES:
        flags.append(f"unknown severity {finding['severity']!r}")
    if finding["severity"] == "BLOCKER" and finding["reach"] != "reachable":
        flags.append(f"BLOCKER with reach {finding['reach']}: at most SHOULD-FIX")
    if not finding["evidence"].strip():
        flags.append("no evidence: treat as a QUESTION")
    return flags


def table(args: argparse.Namespace) -> str:
    """Render every report file as one markdown document."""
    out = []
    for report_path in args.reports:
        report = json.loads(Path(report_path).read_text())
        out += report_lines(Path(report_path).stem, report)
    return "\n".join(out)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("create")
    make.add_argument("name")
    mode = make.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ref")
    mode.add_argument("--working-tree", action="store_true")
    make.add_argument("--base", help="required with --ref")
    make.add_argument("--path", action="append", default=[])
    make.add_argument("--link", action="append", default=[])
    make.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    drop = sub.add_parser("remove")
    drop.add_argument("name")
    drop.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    render = sub.add_parser("table")
    render.add_argument("reports", nargs="+")
    args = parser.parse_args(argv)
    if args.command == "create" and args.ref and not args.base:
        parser.error("--ref needs --base")
    if args.command == "create" and args.working_tree and args.base:
        parser.error("--base is HEAD in --working-tree mode")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand; print its JSON or markdown; return the exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "table":
            print(table(args))
            return 0
        action = create if args.command == "create" else remove
        print(json.dumps(action(args, Path.cwd()), indent=2))
        return 0
    except SnapshotError as error:
        print(f"review_snapshot: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
