#!/usr/bin/env python3
"""Tests for skills/custom/repo-map/repo_map.py (#28).

The tool imports tree-sitter lazily, so the algorithm (PageRank, graph building,
capture processing, render, cache, file discovery) is unit-tested here WITHOUT
the parsers. One integration test exercises real parsing and is skipped unless
tree-sitter + grammars are importable (e.g. run via `uv run --with ...`).
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SKILL = REPO / "skills" / "custom" / "repo-map"
sys.path.insert(0, str(_SKILL))
import repo_map as rm  # noqa: E402


# --- PageRank --------------------------------------------------------------


def test_pagerank_empty():
    assert rm.pagerank([], []) == {}


def test_pagerank_central_node_wins():
    nodes = ["a", "b", "c"]
    edges = [("b", "a", 2.0), ("c", "a", 1.0)]
    pr = rm.pagerank(nodes, edges)
    assert pr["a"] > pr["b"]
    assert pr["a"] > pr["c"]
    assert abs(sum(pr.values()) - 1.0) < 1e-6


def test_pagerank_personalization_biases():
    nodes = ["a", "b"]
    edges = []  # no links: rank is driven purely by the teleport vector
    pr = rm.pagerank(nodes, edges, personalization={"a": 9.0, "b": 1.0})
    assert pr["a"] > pr["b"]


def test_pagerank_handles_dangling_nodes():
    # 'a' has no out-edges (dangling); must not blow up or leak rank.
    pr = rm.pagerank(["a", "b"], [("b", "a", 1.0)])
    assert abs(sum(pr.values()) - 1.0) < 1e-6


# --- graph + personalization ----------------------------------------------


def _tags():
    return {
        "a.py": {"defs": [("alpha", 1, "def alpha():")], "refs": {"beta": 2}},
        "b.py": {"defs": [("beta", 1, "def beta():")], "refs": {"alpha": 1}},
        "c.py": {"defs": [], "refs": {"alpha": 3}},
    }


def test_graph_from_tags_edges_and_refs():
    nodes, edges, global_refs = rm._graph_from_tags(_tags())
    assert set(nodes) == {"a.py", "b.py", "c.py"}
    # a refs beta(def in b) -> edge a->b weight 2; b refs alpha -> b->a w1; c->a w3
    assert ("a.py", "b.py", 2.0) in edges
    assert ("b.py", "a.py", 1.0) in edges
    assert ("c.py", "a.py", 3.0) in edges
    assert global_refs["alpha"] == 4 and global_refs["beta"] == 2


def test_graph_aggregates_edges_per_pair():
    # Two distinct names defined in b and referenced from a -> ONE aggregated edge.
    tags = {
        "a.py": {"defs": [], "refs": {"beta": 2, "gamma": 3}},
        "b.py": {
            "defs": [("beta", 1, "def beta():"), ("gamma", 2, "def gamma():")],
            "refs": {},
        },
    }
    _nodes, edges, _gr = rm._graph_from_tags(tags)
    ab = [e for e in edges if e[0] == "a.py" and e[1] == "b.py"]
    assert ab == [("a.py", "b.py", 5.0)]  # 2 + 3 aggregated, not two edges


def test_graph_skips_ubiquitous_names():
    # A name defined in > MAX_DEFINERS files builds no edges (too common).
    defs_files = {
        f"d{i}.py": {"defs": [("common", 1, "def common():")], "refs": {}}
        for i in range(rm.MAX_DEFINERS + 1)
    }
    defs_files["user.py"] = {"defs": [], "refs": {"common": 5}}
    _nodes, edges, _gr = rm._graph_from_tags(defs_files)
    assert edges == []


def test_graph_skips_self_reference():
    tags = {"s.py": {"defs": [("foo", 1, "def foo():")], "refs": {"foo": 5}}}
    _nodes, edges, _gr = rm._graph_from_tags(tags)
    assert edges == []  # a file referencing its own symbol adds no edge


def test_personalization_boosts_focus_and_recent():
    nodes = ["x.py", "y.py", "z.py"]
    vec = rm._personalization(nodes, focus=["x.py"], recent={"y.py"})
    assert vec["x.py"] > vec["y.py"] > vec["z.py"]


# --- capture processing ----------------------------------------------------


class FakeNode:
    def __init__(self, text: str, row: int):
        self._t = text.encode()
        self.start_point = (row, 0)

    @property
    def text(self):
        return self._t


def test_process_captures_defs_and_refs():
    lines = [b"def alpha(x):", b"    return beta(x)"]
    caps = {
        "name.definition.function": [FakeNode("alpha", 0)],
        "name.reference.call": [FakeNode("beta", 1)],
    }
    defs, refs = rm._process_captures(caps, lines)
    assert defs == [("alpha", 1, "def alpha(x):")]
    assert refs == {"beta": 1}


def test_process_captures_dedups_same_name_same_row():
    lines = [b"class W: pass"]
    caps = {"name.definition.class": [FakeNode("W", 0), FakeNode("W", 0)]}
    defs, _refs = rm._process_captures(caps, lines)
    assert len(defs) == 1


# --- render ----------------------------------------------------------------


def _ranked():
    return [
        ("a.py", "alpha", 1, "def alpha():", 9.0),
        ("a.py", "beta", 5, "def beta():", 8.0),
        ("b.py", "gamma", 2, "def gamma():", 1.0),
    ]


def test_render_groups_by_file_and_orders_by_rank():
    out = rm.render(_ranked(), Path("/repo"), budget_tokens=1000, total_symbols=3)
    assert "# Repo map — /repo (3 of 3 symbols" in out
    # a.py (higher rank) listed before b.py
    assert out.index("a.py\n") < out.index("b.py\n")
    assert "  1: def alpha():" in out and "  5: def beta():" in out


def test_render_respects_budget():
    out = rm.render(_ranked(), Path("/r"), budget_tokens=1, total_symbols=3)
    # budget of 1 token keeps only the first symbol (always emits at least one)
    assert "1 of 3 symbols" in out


def test_render_collapses_multiple_defs_on_one_line():
    ranked = [
        ("u.js", "Base", 3, "class Base { render() {} }", 5.0),
        ("u.js", "render", 3, "class Base { render() {} }", 4.0),
    ]
    out = rm.render(ranked, Path("/r"), budget_tokens=1000, total_symbols=2)
    assert out.count("class Base { render() {} }") == 1


# --- file discovery + cache ------------------------------------------------


def test_list_files_walks_and_filters(tmp_path):
    (tmp_path / "keep.py").write_text("x=1")
    (tmp_path / "keep.ts").write_text("const x=1")
    (tmp_path / "skip.md").write_text("# no")
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "ignored.js").write_text("//no")
    found = {p.name for p in rm.list_files(tmp_path, max_files=100)}
    assert "keep.py" in found and "keep.ts" in found
    assert "skip.md" not in found
    assert "ignored.js" not in found  # node_modules skipped


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / "proj"
    root.mkdir()
    files = {
        "a.py": {"sig": [1, 2], "defs": [["alpha", 1, "def alpha():"]], "refs": {}}
    }
    rm.save_cache(root, files, use_cache=True)
    # JSON has no tuples: defs come back as lists, which the graph/render unpack.
    assert rm.load_cache(root, use_cache=True) == files
    # use_cache=False ignores it
    assert rm.load_cache(root, use_cache=False) == {}


# --- integration (needs the real parsers) ----------------------------------


def test_integration_python_map(tmp_path, capsys):
    pytest.importorskip("tree_sitter")
    pytest.importorskip("tree_sitter_python")
    (tmp_path / "m.py").write_text(
        "def alpha(x):\n    return beta(x)\n\ndef beta(y):\n    return y\n"
    )
    rc = rm.main(["--root", str(tmp_path), "--no-cache", "--budget", "500"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "def alpha(x):" in out
    assert "def beta(y):" in out
