"""Tests for core/skills/codex-snapshot-review/review_snapshot.py.

Each test builds a throwaway git repository under tmp_path, so the snapshot refs,
the temporary index and the worktree are exercised against real git.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "core" / "skills" / "codex-snapshot-review"
sys.path.insert(0, str(SKILL))
import review_snapshot as rs  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


def run(*args: str, cwd: Path) -> str:
    """Run git in `cwd` with a fixed identity and no user config."""
    env = {**os.environ, **GIT_ENV}
    out = subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                         capture_output=True, text=True)
    return out.stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo with main (a.txt, b.txt, .gitignore) and a branch `feature`."""
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "proj"
    root.mkdir()
    run("init", "-q", "-b", "main", cwd=root)
    (root / "a.txt").write_text("a1\n")
    (root / "b.txt").write_text("b1\n")
    (root / ".gitignore").write_text(".env\n")
    run("add", ".", cwd=root)
    run("commit", "-q", "-m", "base", cwd=root)
    run("switch", "-q", "-c", "feature", cwd=root)
    (root / "a.txt").write_text("a2\n")
    run("commit", "-q", "-am", "feature", cwd=root)
    run("switch", "-q", "main", cwd=root)
    (root / "b.txt").write_text("b2\n")
    run("commit", "-q", "-am", "main moves on", cwd=root)
    monkeypatch.chdir(root)
    return root


def cli(*argv: str) -> int:
    """Call the script's main with an argv list."""
    return rs.main(list(argv))


def created(capsys) -> dict:
    """Parse the JSON that `create` printed."""
    return json.loads(capsys.readouterr().out)


def test_ref_mode_pins_head_and_merge_base(repo, tmp_path, capsys):
    """The base is the merge base, so the review diff ignores later base commits."""
    assert cli("create", "f", "--ref", "feature", "--base", "main",
               "--root", str(tmp_path / "wt")) == 0
    out = created(capsys)
    assert out["head"] == run("rev-parse", "feature", cwd=repo)
    assert out["base"] == run("merge-base", "main", "feature", cwd=repo)
    assert run("diff", "--name-only", out["base"], out["head"], cwd=repo) == "a.txt"
    worktree = Path(out["worktree"])
    assert worktree == tmp_path / "wt" / "proj" / "review-f"
    assert run("rev-parse", "HEAD", cwd=worktree) == out["head"]
    assert run("rev-parse", "refs/review/f/head", cwd=repo) == out["head"]


def test_working_tree_mode_leaves_index_and_tree_untouched(repo, tmp_path, capsys):
    """Staged, unstaged and untracked work is pinned; the user's state is not moved."""
    (repo / "a.txt").write_text("staged\n")
    run("add", "a.txt", cwd=repo)
    (repo / "b.txt").write_text("unstaged\n")
    (repo / "c.txt").write_text("new\n")
    (repo / ".env").write_text("SECRET=1\n")
    def state():
        return run("status", "--porcelain", cwd=repo), run("diff", "--cached", cwd=repo)

    before = state()
    assert cli("create", "w", "--working-tree", "--root", str(tmp_path / "wt")) == 0
    out = created(capsys)
    assert state() == before
    assert out["base"] == run("rev-parse", "HEAD", cwd=repo)
    worktree = Path(out["worktree"])
    assert (worktree / "a.txt").read_text() == "staged\n"
    assert (worktree / "b.txt").read_text() == "unstaged\n"
    assert (worktree / "c.txt").read_text() == "new\n"
    assert not (worktree / ".env").exists()


def test_working_tree_mode_honours_path_filter(repo, tmp_path, capsys):
    """Only the named paths enter the snapshot; the rest stays at HEAD."""
    (repo / "a.txt").write_text("changed\n")
    (repo / "b.txt").write_text("changed\n")
    assert cli("create", "p", "--working-tree", "--path", "a.txt",
               "--root", str(tmp_path / "wt")) == 0
    worktree = Path(created(capsys)["worktree"])
    assert (worktree / "a.txt").read_text() == "changed\n"
    assert (worktree / "b.txt").read_text() == "b2\n"


def test_working_tree_mode_refuses_an_empty_snapshot(repo, tmp_path, capsys):
    """A clean tree has nothing to review, and no refs are written."""
    assert cli("create", "e", "--working-tree", "--root", str(tmp_path / "wt")) == 1
    assert "nothing to review" in capsys.readouterr().err
    assert run("for-each-ref", "refs/review/", cwd=repo) == ""


def test_create_refuses_an_existing_name(repo, tmp_path, capsys):
    """A second create under the same name fails before it writes anything."""
    root = str(tmp_path / "wt")
    assert cli("create", "x", "--ref", "feature", "--base", "main", "--root", root) == 0
    assert cli("create", "x", "--ref", "main", "--base", "main", "--root", root) == 1
    assert "exists" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["../up", "a/b", "-flag", "x.lock", "a..b", ""])
def test_unsafe_names_are_refused(name):
    """Names that would escape refs/review/ or break a ref are rejected."""
    with pytest.raises(rs.SnapshotError):
        rs.ref_names(name)


def test_worktree_is_added_without_git_hooks(repo, tmp_path, capsys):
    """A post-checkout hook that seeds worktrees (e.g. copies .env) never runs."""
    hook = repo / ".git" / "hooks" / "post-checkout"
    hook.write_text("#!/bin/sh\ntouch seeded-by-hook\n")
    hook.chmod(0o755)
    assert cli("create", "h", "--ref", "feature", "--base", "main",
               "--root", str(tmp_path / "wt")) == 0
    assert not (Path(created(capsys)["worktree"]) / "seeded-by-hook").exists()


def test_link_then_remove_cleans_everything(repo, tmp_path, capsys):
    """A linked, unignored directory does not block removal; refs go too."""
    (repo / ".venv").mkdir()
    root = str(tmp_path / "wt")
    assert cli("create", "l", "--ref", "feature", "--base", "main",
               "--link", ".venv", "--root", root) == 0
    worktree = Path(created(capsys)["worktree"])
    assert (worktree / ".venv").resolve() == (repo / ".venv").resolve()
    assert cli("remove", "l", "--root", root) == 0
    assert not worktree.exists()
    assert (repo / ".venv").is_dir()
    assert run("for-each-ref", "refs/review/", cwd=repo) == ""


def test_missing_link_source_writes_nothing(repo, tmp_path, capsys):
    """A bad --link fails before any ref or worktree exists."""
    assert cli("create", "m", "--ref", "feature", "--base", "main",
               "--link", "no-such-dir", "--root", str(tmp_path / "wt")) == 1
    assert run("for-each-ref", "refs/review/", cwd=repo) == ""
    assert not (tmp_path / "wt" / "proj" / "review-m").exists()


def test_failure_after_refs_rolls_back(repo, tmp_path, capsys):
    """A link that collides with a tracked file undoes the refs and the worktree."""
    assert cli("create", "r", "--ref", "feature", "--base", "main",
               "--link", "b.txt", "--root", str(tmp_path / "wt")) == 1
    assert "already exists" in capsys.readouterr().err
    assert run("for-each-ref", "refs/review/", cwd=repo) == ""
    assert not (tmp_path / "wt" / "proj" / "review-r").exists()


def test_remove_keeps_a_dirty_snapshot(repo, tmp_path, capsys):
    """An edited snapshot is not removed, and its refs stay for inspection."""
    root = str(tmp_path / "wt")
    assert cli("create", "d", "--ref", "feature", "--base", "main", "--root", root) == 0
    worktree = Path(created(capsys)["worktree"])
    (worktree / "a.txt").write_text("edited by the reviewer\n")
    assert cli("remove", "d", "--root", root) == 1
    assert worktree.exists()
    assert "refs/review/d/head" in run("for-each-ref", "refs/review/", cwd=repo)


def finding(**overrides) -> dict:
    """A schema-shaped finding with every field filled."""
    base = {"severity": "SHOULD-FIX", "file": "src/x.py", "line": 7,
            "claim": "x drops y", "failure_scenario": "y=0 -> crash",
            "reach": "latent", "reachable_from": "no route sets y",
            "why_not_by_design": "manifest silent", "evidence": "probe: crash",
            "suggested_test": "test y=0", "fix": "guard y"}
    return {**base, **overrides}


def write_report(path: Path, findings: list[dict]) -> Path:
    """Write a schema-shaped report."""
    path.write_text(json.dumps({
        "verdict": "mergeable-after-fixes", "summary": "ok | mostly",
        "findings": findings, "checked_and_sound": ["order"], "not_checked": ["0.8.5"],
    }))
    return path


def test_table_numbers_rows_and_escapes_cells(tmp_path, capsys):
    """Ids come from the report name; pipes and newlines cannot break the table."""
    rows = [finding(claim="a | b\nc"), finding(line=None, file="PR body")]
    report = write_report(tmp_path / "pr1.json", rows)
    assert cli("table", str(report)) == 0
    out = capsys.readouterr().out
    assert "| pr1-1 | `src/x.py:7` a \\| b c (SHOULD-FIX -> ?) | latent: " in out
    assert "| pr1-2 | `PR body` x drops y" in out
    assert "ok \\| mostly" in out
    assert "Flags for triage: none" in out
    assert "- 0.8.5" in out


def test_table_flags_a_blocker_that_is_not_reachable(tmp_path, capsys):
    """The rating rule is checked mechanically: BLOCKER needs reach == reachable."""
    report = write_report(tmp_path / "pr2.json", [
        finding(severity="BLOCKER", reach="latent"),
        finding(severity="BLOCKER", reach="reachable", reachable_from="job -> f"),
        finding(evidence="  "),
    ])
    assert cli("table", str(report)) == 0
    out = capsys.readouterr().out
    assert "- pr2-1: BLOCKER with reach latent: at most SHOULD-FIX" in out
    assert "pr2-2:" not in out.split("Flags for triage:")[1]
    assert "- pr2-3: no evidence: treat as a QUESTION" in out


def objects(node):
    """Yield every object schema inside a JSON schema."""
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for value in node.values():
            yield from objects(value)
    elif isinstance(node, list):
        for value in node:
            yield from objects(value)


def test_schema_meets_strict_structured_output_rules():
    """Strict structured output needs every property required and no extras."""
    schema = json.loads((SKILL / "findings.schema.json").read_text())
    found = list(objects(schema))
    assert len(found) == 2
    for node in found:
        assert node["additionalProperties"] is False
        assert sorted(node["required"]) == sorted(node["properties"])


def test_schema_and_table_agree_on_severities():
    """The script's severity list is the schema's enum."""
    schema = json.loads((SKILL / "findings.schema.json").read_text())
    enum = schema["properties"]["findings"]["items"]["properties"]["severity"]["enum"]
    assert tuple(enum) == rs.SEVERITIES
