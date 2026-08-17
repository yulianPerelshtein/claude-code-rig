#!/usr/bin/env python3
"""Tests for core/routines/self_check.py.

The import-closure tests matter most: the first version of that parser matched
only line-leading `@`, so it reported "all 2 Layer-1 files loaded" for a
five-file chain and would have passed while Layer 1 was half-loaded. A check
that can only succeed is worse than no check.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "core" / "routines" / "self_check.py"
BLOCKLIST = REPO / "core" / "hooks" / "blocked-commands.json"
PROBES = REPO / "core" / "hooks" / "guardrail-probes.json"

_spec = importlib.util.spec_from_file_location("self_check", MODULE)
sc = importlib.util.module_from_spec(_spec)
sys.modules["self_check"] = sc  # dataclasses resolve types via sys.modules
_spec.loader.exec_module(sc)


def write(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


# ── import closure ────────────────────────────────────────────────────────────


def test_follows_inline_imports_not_just_line_leading(tmp_path):
    """CLAUDE.base.md writes siblings as `- @safety-rules.md`."""
    write(tmp_path / "sib.md", "sibling")
    entry = write(tmp_path / "CLAUDE.md", "- @sib.md — a sibling\n")
    files, broken = sc.import_closure(entry)
    assert (tmp_path / "sib.md").resolve() in files
    assert broken == []


def test_follows_a_multi_hop_chain(tmp_path):
    write(tmp_path / "c.md", "leaf")
    write(tmp_path / "b.md", "- @c.md\n")
    entry = write(tmp_path / "a.md", "@b.md\n")
    files, _ = sc.import_closure(entry)
    assert {p.name for p in files} == {"a.md", "b.md", "c.md"}


def test_ignores_imports_inside_code_spans_and_fences(tmp_path):
    entry = write(
        tmp_path / "CLAUDE.md",
        "Write `@notreal.md` to mention it.\n\n```\n@alsonotreal.md\n```\n",
    )
    files, broken = sc.import_closure(entry)
    assert files == {entry.resolve()}
    assert broken == []


def test_ignores_email_addresses(tmp_path):
    entry = write(tmp_path / "CLAUDE.md", "Contact someone@example.com for access.\n")
    files, broken = sc.import_closure(entry)
    assert files == {entry.resolve()}
    assert broken == []


def test_reports_a_dangling_import_instead_of_dropping_it(tmp_path):
    """Silently shrinking the expected set is how the check would pass while
    Layer 1 was broken."""
    entry = write(tmp_path / "CLAUDE.md", "@missing.md\n")
    files, broken = sc.import_closure(entry)
    assert files == {entry.resolve()}
    assert len(broken) == 1 and "missing.md" in broken[0]


def test_survives_an_import_cycle(tmp_path):
    write(tmp_path / "b.md", "@a.md\n")
    entry = write(tmp_path / "a.md", "@b.md\n")
    files, _ = sc.import_closure(entry)
    assert {p.name for p in files} == {"a.md", "b.md"}


# ── CI pin detection ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "line,flagged",
    [
        ("        run: uv tool install ruff", True),
        ("        run: pip install yamllint", True),
        ("        run: npm install -g markdownlint-cli", True),
        ("        run: uv tool install ruff==0.7.4", False),
        ("        run: npm install -g markdownlint-cli@0.43.0", False),
        ("        run: pip install yamllint==1.35.1", False),
    ],
)
def test_unpinned_tool_detection(line, flagged):
    assert bool(sc.UNPINNED_RE.search(line)) is flagged


# ── probe fixture integrity ───────────────────────────────────────────────────


def test_every_blocklist_pattern_has_a_probe():
    """Keeps the probe fixture honest: a new guardrail rule without a probe is
    an untested rule, and self-check would otherwise imply full coverage."""
    patterns = {p["regex"] for p in json.loads(BLOCKLIST.read_text())["patterns"]}
    covered = {p.get("covers") for p in json.loads(PROBES.read_text())["blocked"]}
    orphans = patterns - covered
    assert orphans == set(), f"blocklist patterns with no probe: {orphans}"


def test_probe_covers_fields_match_real_patterns():
    """A typo'd `covers` would silently count as covering nothing."""
    patterns = {p["regex"] for p in json.loads(BLOCKLIST.read_text())["patterns"]}
    blocked = json.loads(PROBES.read_text())["blocked"]
    covered = {p["covers"] for p in blocked if p.get("covers")}
    stale = covered - patterns
    assert stale == set(), f"`covers` values matching no pattern: {stale}"


# ── delivery paths ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command,expected",
    [
        ("bash ~/rig/core/statusline/statusline.sh", "statusline.sh"),
        ("/usr/bin/bash /opt/rig/sl.sh --flag", "sl.sh"),
        ("python3 /opt/rig/sl.py", None),
        ("", None),
    ],
)
def test_statusline_script_extraction(command, expected):
    """Which checkout the statusline loads from decides whether it can drift
    from Layer 1; that answer starts with parsing the configured command."""
    found = sc.statusline_script(command)
    assert (found.name if found else None) == expected


def test_statusline_script_expands_home():
    found = sc.statusline_script("bash ~/rig/sl.sh")
    assert found is not None and not str(found).startswith("~")


# ── purged history ────────────────────────────────────────────────────────────


def _mock_run(code):
    """A subprocess result carrying just an HTTP status code (curl branch)."""
    return lambda *a, **k: type("P", (), {"stdout": code, "stderr": ""})()


def test_history_purged_skips_when_nothing_is_declared_purged(monkeypatch, tmp_path):
    """No declared list means no claim to verify — skip, never a silent pass."""
    monkeypatch.setattr(sc, "PURGED_SHAS", tmp_path / "absent.txt")
    r = sc.check_history_purged()
    assert r.status == sc.SKIP


def test_history_purged_skips_on_an_empty_list(monkeypatch, tmp_path):
    f = tmp_path / "purged.txt"
    f.write_text("# only comments\n\n")
    monkeypatch.setattr(sc, "PURGED_SHAS", f)
    assert sc.check_history_purged().status == sc.SKIP


def test_history_purged_fails_when_the_remote_still_serves_one(monkeypatch, tmp_path):
    """The whole point: a 200 means the purge did not take."""
    f = tmp_path / "purged.txt"
    f.write_text("deadbee\n")
    monkeypatch.setattr(sc, "PURGED_SHAS", f)
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setattr(sc, "run", _mock_run("200"))
    r = sc.check_history_purged()
    assert r.status == sc.FAIL and "still served" in r.summary


@pytest.mark.parametrize("code", ["000", "403", "429", "500", ""])
def test_history_purged_never_passes_on_a_non_404(monkeypatch, tmp_path, code):
    """Only 404 proves a commit is gone.

    An earlier version counted anything that was not 200 as fine, so an API rate
    limit (403) made this report clean while orphaned commits were live.
    """
    f = tmp_path / "purged.txt"
    f.write_text("deadbee\n")
    monkeypatch.setattr(sc, "PURGED_SHAS", f)
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setattr(sc, "run", _mock_run(code))
    assert sc.check_history_purged().status == sc.SKIP


@pytest.mark.parametrize("code", ["404", "422"])
def test_history_purged_passes_on_gone_codes(monkeypatch, tmp_path, code):
    """422 is what the commits endpoint returns for an absent commit."""
    f = tmp_path / "purged.txt"
    f.write_text("deadbee\n")
    monkeypatch.setattr(sc, "PURGED_SHAS", f)
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.setattr(sc, "run", _mock_run(code))
    assert sc.check_history_purged().status == sc.PASS



# ── report rendering ──────────────────────────────────────────────────────────


def test_render_marks_the_run_failed_when_any_check_fails():
    results = [
        sc.CheckResult("a", sc.PASS, "fine"),
        sc.CheckResult("b", sc.FAIL, "broken", ["detail"]),
    ]
    out = sc.render(results)
    assert out.startswith("# rig self-check — FAIL")
    assert "1 failed, 1 passed, 0 skipped." in out
    assert "- `detail`" in out


def test_render_passes_when_only_skips_remain():
    results = [
        sc.CheckResult("a", sc.PASS, "fine"),
        sc.CheckResult("b", sc.SKIP, "n/a"),
    ]
    out = sc.render(results)
    assert out.startswith("# rig self-check — PASS")
