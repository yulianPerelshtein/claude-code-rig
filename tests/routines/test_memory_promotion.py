#!/usr/bin/env python3
"""Tests for core/routines/memory_promotion.py.

The detector is deliberately narrow: it reports the same slug in two projects,
and `type: feedback`/`user`. It does NOT decide whether the rig already carries
a rule — three attempts at that by word overlap each produced confident nonsense
(a mutation-testing memory cited to a PR-hygiene doc at 85%), so the judgement
moved to /weekly-retro. These tests pin the narrowness as much as the behaviour.
"""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "core" / "routines" / "memory_promotion.py"

_spec = importlib.util.spec_from_file_location("memory_promotion", MODULE)
mp = importlib.util.module_from_spec(_spec)
sys.modules["memory_promotion"] = mp
_spec.loader.exec_module(mp)


def memory(project: str, slug: str, mtype: str, description: str = "") -> "mp.Memory":
    return mp.Memory(project, slug, Path(f"/x/{slug}.md"), mtype, description)


# ── which memories are even candidates ────────────────────────────────────────


def test_project_and_reference_memories_are_never_candidates():
    """`project`/`reference` are local by definition; only guidance travels."""
    mems = [
        memory("p1", "local-db-quirk", "project"),
        memory("p1", "runbook-url", "reference"),
    ]
    buckets = mp.classify(mems, {}, decided={})
    assert buckets["duplicated"] == []
    assert buckets["candidates"] == []


def test_feedback_and_user_memories_are_candidates():
    mems = [memory("p1", "style-pref", "feedback"), memory("p2", "who-i-am", "user")]
    buckets = mp.classify(mems, {}, decided={})
    assert {row[0] for row in buckets["candidates"]} == {"style-pref", "who-i-am"}


def test_same_slug_in_two_projects_is_the_duplication_signal():
    """The one signal needing no judgement — and the real case that motivated
    this: commit-message-conventions written out once per repo."""
    mems = [
        memory("p1", "commit-message-conventions", "feedback"),
        memory("p2", "commit-message-conventions", "feedback"),
    ]
    buckets = mp.classify(mems, {}, decided={})
    assert [row[0] for row in buckets["duplicated"]] == ["commit-message-conventions"]
    assert buckets["candidates"] == []


def test_a_slug_in_one_project_is_not_duplication():
    buckets = mp.classify([memory("p1", "only-here", "feedback")], {}, decided={})
    assert buckets["duplicated"] == []
    assert [row[0] for row in buckets["candidates"]] == ["only-here"]


# ── the decisions ledger ──────────────────────────────────────────────────────


def test_a_judged_memory_stops_being_a_candidate():
    """A weekly report that repeats last week's answers stops being read."""
    mems = [memory("p1", "already-done", "feedback")]
    decided = {"already-done": {"verdict": "promoted", "date": "2026-08-16"}}
    buckets = mp.classify(mems, {}, decided=decided)
    assert buckets["candidates"] == []
    assert [row[0] for row in buckets["settled"]] == ["already-done"]


def test_a_judged_duplicate_also_settles():
    mems = [
        memory("p1", "seen-twice", "feedback"),
        memory("p2", "seen-twice", "feedback"),
    ]
    decided = {"seen-twice": {"verdict": "local", "date": "2026-08-16"}}
    buckets = mp.classify(mems, {}, decided=decided)
    assert buckets["duplicated"] == []
    assert [row[0] for row in buckets["settled"]] == ["seen-twice"]


def test_report_says_nothing_new_when_everything_is_judged():
    mems = [memory("p1", "already-done", "feedback")]
    decided = {"already-done": {"verdict": "promoted", "date": "2026-08-16"}}
    out = mp.render(mems, mp.classify(mems, {}, decided=decided))
    assert "**Nothing new to judge.**" in out


def test_classify_does_not_read_the_real_ledger_when_one_is_injected(tmp_path):
    """Hidden global reads made an earlier test env-dependent; keep it injected."""
    mems = [memory("p1", "commit-message-conventions", "feedback")]
    buckets = mp.classify(mems, {}, decided={})
    assert [row[0] for row in buckets["candidates"]] == ["commit-message-conventions"]


# ── the detector must not claim coverage ──────────────────────────────────────


def test_classification_never_depends_on_the_rig_corpus():
    """Buckets must be identical with and without a corpus. If a corpus can move
    a memory between buckets, the unsound coverage verdict has crept back in."""
    mems = [memory("p1", "concise-code-comments", "feedback", "short docstrings")]
    corpus = {"core/CLAUDE.base.md": {"concise", "comments", "docstrings", "short"}}
    without = mp.classify(mems, {}, decided={})
    with_rig = mp.classify(mems, corpus, decided={})
    for bucket in ("candidates", "duplicated"):
        assert [r[0] for r in without[bucket]] == [r[0] for r in with_rig[bucket]]


def test_report_states_that_nearest_is_not_a_verdict():
    mems = [memory("p1", "some-pref", "feedback", "a preference")]
    corpus = {"core/CLAUDE.base.md": {"preference", "some"}}
    out = mp.render(mems, mp.classify(mems, corpus, decided={}))
    assert "NOT a claim the rule is already there" in out
    assert "nothing here recommends deleting anything" in out


# ── identity vs description ───────────────────────────────────────────────────


def test_identity_uses_the_slug_not_the_description():
    """Description prose collides with every rig file; the slug is the topic."""
    mem = memory("p1", "mutation-test-the-test", "feedback", "never always prefer")
    assert "mutation" in mem.identity()
    assert "never" not in mem.identity()


def test_distinctive_drops_terms_common_across_the_rig():
    corpus = {f"f{i}.md": {"working", "style"} for i in range(8)}
    corpus["rare.md"] = {"working", "style", "tracemalloc"}
    kept = mp.distinctive({"working", "style", "tracemalloc"}, corpus)
    assert kept == {"tracemalloc"}


# ── project directory hygiene ─────────────────────────────────────────────────


def test_decode_project_dir_round_trips_a_real_path(tmp_path):
    (tmp_path / "home" / "alice" / "work").mkdir(parents=True)
    decoded = mp.decode_project_dir("-home-alice-work", root=tmp_path)
    assert decoded == tmp_path / "home" / "alice" / "work"


def test_decode_project_dir_handles_a_hyphen_inside_a_component(tmp_path):
    """`/` and `-` both encode to `-`, so splitting on every hyphen would decode
    `my-project` as `my/project` and silently stop scanning a real project."""
    (tmp_path / "home" / "my-project").mkdir(parents=True)
    decoded = mp.decode_project_dir("-home-my-project", root=tmp_path)
    assert decoded == tmp_path / "home" / "my-project"


def test_decode_project_dir_returns_none_for_a_vanished_path(tmp_path):
    assert mp.decode_project_dir("-tmp-gone-forever", root=tmp_path) is None


def test_live_project_dirs_skips_projects_whose_path_is_gone(tmp_path, monkeypatch):
    """A headless probe in a temp dir leaves a memory dir behind; counting those
    would manufacture duplication signal out of scratch directories."""
    projects = tmp_path / "projects"
    real = tmp_path / "realproj"
    real.mkdir()
    # Encoded from a real path under tmp_path, which itself contains hyphens
    # (`pytest-of-<user>`) — so this also proves the decoder survives them.
    encoded = str(real).replace("/", "-")
    (projects / encoded / "memory").mkdir(parents=True)
    (projects / "-tmp-gone-forever-nowhere" / "memory").mkdir(parents=True)
    monkeypatch.setattr(mp, "PROJECTS_DIR", projects)
    found = [d.parent.name for d in mp.live_project_dirs()]
    assert found == [encoded]
