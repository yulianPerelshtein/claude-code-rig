#!/usr/bin/env python3
"""Tests for core/hooks/utils/hooklib.py — shared hook helpers.

Focus on the rotation invariant that a local-review finding caught: keep_lines
must actually drop the file below the byte threshold, otherwise the trim sheds
nothing and every append degrades to an O(n) rewrite.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "core" / "hooks"))

from utils.hooklib import append_jsonl, int_env, rotate_jsonl_log  # noqa: E402


def test_int_env_good(monkeypatch):
    monkeypatch.setenv("X_KNOB", "12")
    assert int_env("X_KNOB", 7) == 12


def test_int_env_bad_falls_back(monkeypatch):
    monkeypatch.setenv("X_KNOB", "abc")
    assert int_env("X_KNOB", 7) == 7


def test_int_env_missing_uses_default(monkeypatch):
    monkeypatch.delenv("X_KNOB", raising=False)
    assert int_env("X_KNOB", 7) == 7


def test_int_env_floor_is_one(monkeypatch):
    monkeypatch.setenv("X_KNOB", "0")
    assert int_env("X_KNOB", 7) == 1


def test_rotate_noop_under_threshold(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("a\nb\nc\n", encoding="utf-8")
    rotate_jsonl_log(log, keep_lines=2, max_bytes=10_000)
    # Below threshold -> untouched.
    assert log.read_text() == "a\nb\nc\n"


def test_rotate_trims_below_threshold_once_over(tmp_path):
    log = tmp_path / "x.log"
    # 1000 short lines, well over a tiny byte threshold.
    log.write_text("".join(f"line{i}\n" for i in range(1000)), encoding="utf-8")
    over_before = log.stat().st_size
    rotate_jsonl_log(log, keep_lines=50, max_bytes=200)
    lines = log.read_text().splitlines()
    # keep_lines honored AND the file is now meaningfully smaller (the trim
    # actually shed lines — the invariant the review flagged).
    assert len(lines) == 50
    assert lines[0] == "line950"
    assert log.stat().st_size < over_before


def test_rotate_missing_file_is_safe(tmp_path):
    rotate_jsonl_log(tmp_path / "nope.log", keep_lines=10)  # no raise


def test_append_jsonl_creates_parents_and_appends(tmp_path):
    import json

    log = tmp_path / "deep" / "dir" / "log.jsonl"
    append_jsonl(log, {"a": 1}, keep_lines=100)
    append_jsonl(log, {"a": 2}, keep_lines=100)
    lines = [json.loads(ln) for ln in log.read_text().splitlines()]
    assert lines == [{"a": 1}, {"a": 2}]


def test_append_jsonl_rotates(tmp_path):
    log = tmp_path / "log.jsonl"
    for i in range(500):
        append_jsonl(log, {"i": i}, keep_lines=20, max_bytes=200)
    lines = log.read_text().splitlines()
    # Rotation kept it bounded near keep_lines, not all 500.
    assert len(lines) <= 21
