"""CLI orchestrator: resolve a routine and run it (or preview it with --dry-run).

Outcome enforcement lives in the RUNNER, not the model:
  - report-only / local-write-allowlist: the body runs in the target; for a
    report-only body the runner captures the output and writes the report.
  - draft-pr: the body runs inside an isolated git worktree (the model only
    edits files there); the RUNNER — never the model — commits, pushes the
    feature branch, and opens the DRAFT PR via the policy-gated gitops helpers.

A skill body is invoked as `claude -p "/<body> ..."`; a script body (dream-loop)
runs its shipped deterministic script directly via the same interpreter.
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from .gitops import create_worktree, open_draft_pr, remove_worktree, routine_branch_name
from .policy import PolicyError, assert_path_in_target
from .registry import Routine, load_registry
from .report import append_log, write_report, write_state

STATE_DIR = Path(os.path.expanduser("~/.local/share/cc-rig-routines"))
REPORT_DIR = Path(os.path.expanduser("~/.claude/routine-reports"))
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "registry.yaml"


def rig_root(registry_path: Path) -> Path:
    """registry.yaml lives at <rig>/core/routines/registry.yaml."""
    return registry_path.resolve().parents[2]


def build_invocation(routine: Routine, cwd: Path, registry_path: Path) -> list[str]:
    """The argv the runner executes for this routine."""
    if routine.body_type == "script":
        # same interpreter as the runner (bare "python" may be absent under a
        # minimal systemd-user PATH); the script is stdlib-only.
        return [sys.executable, str(rig_root(registry_path) / routine.script)]
    prompt = (
        f"/{routine.body} --target {cwd} --routine-mode "
        f"--outcome {routine.outcome}"
    )
    return ["claude", "-p", prompt]


def run_body(
    routine: Routine, cwd: Path, registry_path: Path
) -> subprocess.CompletedProcess:
    """Execute the routine body in `cwd`. Injectable seam for tests."""
    return subprocess.run(
        build_invocation(routine, cwd, registry_path),
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _changed_paths(repo: Path) -> list[str]:
    """Paths (relative to `repo`) that `git status --porcelain` reports dirty."""
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        rel = line[3:]
        if " -> " in rel:  # rename: take the destination
            rel = rel.split(" -> ", 1)[1]
        paths.append(rel.strip().strip('"'))
    return paths


def _newest_since(hint: str, since: float) -> str:
    """Newest file matching `hint` (expanduser'd glob) produced at/after `since`.
    Used to record a script body's own report as the run artifact."""
    matches = []
    for path in glob.glob(os.path.expanduser(hint)):
        try:
            if os.stat(path).st_mtime >= since - 1:  # -1: fs mtime granularity
                matches.append(path)
        except OSError:
            continue
    return max(matches, key=lambda p: os.stat(p).st_mtime) if matches else ""


def _run_report_only(
    routine: Routine, target: Path, registry_path: Path, runner, report_dir: Path
) -> tuple[int, str]:
    before = time.time()
    proc = runner(routine, target, registry_path)
    if proc.returncode != 0:
        return proc.returncode, ""
    if routine.body_type == "script":
        # the script writes its own report; resolve it via the registry hint
        # (the shipped dream_loop.py does NOT print its path to stdout), else
        # fall back to a path printed on stdout.
        if routine.artifact_hint:
            return 0, _newest_since(routine.artifact_hint, before)
        out = (proc.stdout or "").strip().splitlines()
        return 0, (out[-1] if out else "")
    path = write_report(report_dir, routine.name, proc.stdout or "")
    return 0, str(path)


def _run_draft_pr(
    routine: Routine, target: Path, registry_path: Path, runner, pr_opener
) -> tuple[int, str]:
    """Model edits inside an isolated worktree; the RUNNER opens the draft PR."""
    branch = routine_branch_name(routine.name, date.today().isoformat())
    worktree = create_worktree(target, branch)
    try:
        proc = runner(routine, worktree, registry_path)
        if proc.returncode != 0:
            return proc.returncode, ""
        changed = _changed_paths(worktree)
        if not changed:
            return 0, "(no changes — no PR opened)"
        # defence-in-depth: every edit must resolve inside the worktree (catches a
        # body that escapes via an absolute path / symlink before we commit).
        for rel in changed:
            assert_path_in_target((worktree / rel).resolve(), worktree)
        subprocess.run(["git", "-C", str(worktree), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(worktree), "commit", "-m", f"routine: {routine.name}"],
            check=True,
            capture_output=True,
        )
        url = pr_opener(
            target,
            branch,
            f"routine: {routine.name}",
            f"Automated {routine.name} draft PR.",
        )
        return 0, url
    finally:
        remove_worktree(target, worktree)


def execute(
    routine: Routine,
    target: Path,
    registry_path: Path,
    *,
    runner=run_body,
    pr_opener=open_draft_pr,
) -> int:
    """Run one routine under its outcome policy. Never raises; records run-state.

    State + report directories are the module globals STATE_DIR / REPORT_DIR
    (tests monkeypatch them); `runner` / `pr_opener` are the injectable seams so
    the orchestration is unit-tested without claude / gh / network."""
    append_log(STATE_DIR, f"start {routine.name} target={target}")
    artifact = ""
    try:
        if routine.outcome == "draft-pr":
            rc, artifact = _run_draft_pr(
                routine, target, registry_path, runner, pr_opener
            )
        else:
            rc, artifact = _run_report_only(
                routine, target, registry_path, runner, REPORT_DIR
            )
        status = "ok" if rc == 0 else f"rc={rc}"
    except (PolicyError, OSError, subprocess.SubprocessError) as exc:
        rc, status = 1, f"error: {type(exc).__name__}"
        append_log(STATE_DIR, f"error {routine.name}: {exc}")
    write_state(STATE_DIR, routine.name, status=status, artifact=artifact)
    append_log(STATE_DIR, f"end {routine.name} rc={rc}")
    return rc


def _parse_args(argv) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="run-routine")
    ap.add_argument("name")
    # Default None so main() can distinguish "not supplied" (resolve from the
    # routine's target_default) from an explicit --target the caller passed.
    ap.add_argument("--target", default=None)
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args(argv)


def resolve_target(routine: Routine, explicit: str | None, registry_path: Path) -> Path:
    """Where the routine runs. An explicit --target always wins; otherwise honor
    the routine's declared target_default (`rig` -> the rig repo, `cwd` -> the
    caller's working directory). Without this, a `rig`-targeted routine
    (weekly-retro, monthly-drift) would silently run against whatever cwd the
    caller happened to be in — e.g. opening a draft PR on the wrong repo."""
    if explicit is not None:
        return Path(explicit).resolve()
    if routine.target_default == "rig":
        return rig_root(registry_path)
    return Path(os.getcwd()).resolve()


def main(argv=None) -> int:
    args = _parse_args(argv)
    registry_path = Path(args.registry)
    reg = load_registry(registry_path)
    if args.name not in reg:
        print(f"unknown routine: {args.name}", file=sys.stderr)
        return 2
    routine = reg[args.name]
    if not routine.enabled:
        print(f"routine disabled: {args.name}", file=sys.stderr)
        return 3
    target = resolve_target(routine, args.target, registry_path)

    if args.dry_run:
        invocation = build_invocation(routine, target, registry_path)
        print(
            f"[dry-run] routine={routine.name} body_type={routine.body_type} "
            f"outcome={routine.outcome} target={target}"
        )
        print(f"[dry-run] would run: {' '.join(invocation)}")
        return 0

    return execute(routine, target, registry_path)


if __name__ == "__main__":
    raise SystemExit(main())
