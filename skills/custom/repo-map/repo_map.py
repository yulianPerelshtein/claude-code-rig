#!/usr/bin/env python3
"""Local repo-map — a ranked, token-budgeted orientation map of a repository.

Reproduces Aider's repo-map algorithm with NO dependency on the stale grep-ast:

  tree-sitter tags  ->  file-reference graph  ->  weighted PageRank
  (task-aware personalization)  ->  greedy token-budgeted, signatures-only render.

Local, zero-egress; the always-on *orientation* map that serena's on-demand
symbol lookup doesn't give you. PageRank is a self-contained power iteration (no
numpy/scipy/networkx) so cold-start stays cheap.

Run via uv so the parsers are fetched on demand (no global install):

  uv run --with tree-sitter --with tree-sitter-python \\
         --with tree-sitter-javascript --with tree-sitter-typescript \\
         python repo_map.py --root . [--focus PATH ...] [--budget 1024]

Languages: Python, JavaScript/JSX, TypeScript/TSX. Skips unparsable files; prints
a map (or a clear reason) and never crashes on a single bad file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# --- language config -------------------------------------------------------

# extension -> internal language key
LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}

# Per-language tree-sitter tag patterns. Captures follow Aider's convention:
# @name.definition.* (a symbol defined here) and @name.reference.* (a use).
# Stored as INDIVIDUAL patterns and compiled one-by-one (see get_query) so a
# single pattern that is "impossible" for a given grammar version is dropped
# rather than killing the whole language — resilience to grammar drift.
PY_PATTERNS = [
    "(function_definition name: (identifier) @name.definition.function)",
    "(class_definition name: (identifier) @name.definition.class)",
    "(call function: (identifier) @name.reference.call)",
    "(call function: (attribute attribute: (identifier) @name.reference.call))",
]
JS_PATTERNS = [
    "(function_declaration name: (identifier) @name.definition.function)",
    "(generator_function_declaration name: (identifier) @name.definition.function)",
    "(method_definition name: (property_identifier) @name.definition.method)",
    "(class_declaration name: (identifier) @name.definition.class)",
    "(variable_declarator name: (identifier) @name.definition.function"
    " value: [(arrow_function) (function_expression)])",
    "(call_expression function: (identifier) @name.reference.call)",
    "(call_expression function: (member_expression"
    " property: (property_identifier) @name.reference.call))",
    "(new_expression constructor: (identifier) @name.reference.class)",
]
TS_EXTRA = [
    "(interface_declaration name: (type_identifier) @name.definition.interface)",
    "(type_alias_declaration name: (type_identifier) @name.definition.type)",
    "(function_signature name: (identifier) @name.definition.function)",
]
TAG_PATTERNS = {
    "python": PY_PATTERNS,
    "javascript": JS_PATTERNS,
    "typescript": JS_PATTERNS + TS_EXTRA,
    "tsx": JS_PATTERNS + TS_EXTRA,
}

# Definitions worth showing in the map (references never render, they only
# build the graph). All capture kinds under name.definition.* qualify.
MAX_SIG_LEN = 120
DEFAULT_BUDGET_TOKENS = 1024
DEFAULT_MAX_FILES = 5000
DEFAULT_MAX_FILE_BYTES = 2_000_000
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".next", "out",
    "target", ".idea", ".vscode", "vendor",
}
PAGERANK_DAMPING = 0.85
PAGERANK_ITERS = 60
PAGERANK_TOL = 1e-6
# A name defined in more than this many files is too ubiquitous to inform
# centrality (e.g. render/get/main); it still scores, but builds no graph edges.
MAX_DEFINERS = 10
CACHE_VERSION = 2

_LANG_CACHE: dict[str, object] = {}
_PARSER_CACHE: dict[str, object] = {}
_QUERY_CACHE: dict[str, object] = {}


# --- tree-sitter plumbing (lazy; clear error if not run via uv) ------------


def _fatal_missing(exc: Exception) -> None:
    sys.stderr.write(
        f"repo-map: tree-sitter not available ({type(exc).__name__}: {exc}).\n"
        "Run via uv so the parsers are fetched on demand, e.g.:\n"
        "  uv run --with tree-sitter --with tree-sitter-python "
        "--with tree-sitter-javascript --with tree-sitter-typescript "
        "python repo_map.py --root .\n"
    )
    sys.exit(1)


def get_language(key: str):
    if key in _LANG_CACHE:
        return _LANG_CACHE[key]
    import tree_sitter as ts

    if key == "python":
        import tree_sitter_python as m

        lang = ts.Language(m.language())
    elif key == "javascript":
        import tree_sitter_javascript as m

        lang = ts.Language(m.language())
    elif key == "typescript":
        import tree_sitter_typescript as m

        lang = ts.Language(m.language_typescript())
    elif key == "tsx":
        import tree_sitter_typescript as m

        lang = ts.Language(m.language_tsx())
    else:
        raise ValueError(f"unsupported language key: {key}")
    _LANG_CACHE[key] = lang
    return lang


def get_parser(key: str):
    if key not in _PARSER_CACHE:
        import tree_sitter as ts

        _PARSER_CACHE[key] = ts.Parser(get_language(key))
    return _PARSER_CACHE[key]


def get_query(key: str):
    """Build a combined query from the language's patterns, keeping only those
    that compile against the actual grammar (drops 'impossible' patterns for a
    given grammar version instead of failing the whole language). Cached;
    returns None if no pattern compiles."""
    if key not in _QUERY_CACHE:
        import tree_sitter as ts

        lang = get_language(key)
        good = []
        for pat in TAG_PATTERNS[key]:
            try:
                ts.Query(lang, pat)
                good.append(pat)
            except Exception:
                continue
        _QUERY_CACHE[key] = ts.Query(lang, "\n".join(good)) if good else None
    return _QUERY_CACHE[key]


def run_captures(query, root_node) -> dict:
    """Return {capture_name: [nodes]} across tree-sitter API versions."""
    import tree_sitter as ts

    if hasattr(ts, "QueryCursor"):  # tree-sitter >= 0.25
        return ts.QueryCursor(query).captures(root_node)
    return query.captures(root_node)  # older bindings


# --- tag extraction --------------------------------------------------------


def _decode_name(node) -> str:
    try:
        return node.text.decode("utf-8", "replace")
    except Exception:
        return ""


def _process_captures(caps: dict, lines: list[bytes]) -> tuple[list, dict]:
    """Turn {capture: [nodes]} into (defs, refs). defs are (name, line, sig);
    refs is {name: count}."""
    defs: list[tuple[str, int, str]] = []
    refs: dict[str, int] = {}
    seen_def: set[tuple[str, int]] = set()
    for cap_name, nodes in caps.items():
        is_def = ".definition." in cap_name
        for node in nodes:
            name = _decode_name(node)
            if not name:
                continue
            if not is_def:
                refs[name] = refs.get(name, 0) + 1
                continue
            row = node.start_point[0]
            if (name, row) in seen_def:
                continue
            seen_def.add((name, row))
            sig = ""
            if 0 <= row < len(lines):
                sig = lines[row].decode("utf-8", "replace").strip()[:MAX_SIG_LEN]
            defs.append((name, row + 1, sig))
    return defs, refs


def extract_tags(path: Path, key: str) -> dict:
    """Parse one file and return {'defs': [(name, line, sig)], 'refs': {name: n}}.
    Best-effort: any parse failure yields empty tags rather than raising."""
    try:
        data = path.read_bytes()
    except OSError:
        return {"defs": [], "refs": {}}
    try:
        tree = get_parser(key).parse(data)
        query = get_query(key)
        if query is None:
            return {"defs": [], "refs": {}}
        caps = run_captures(query, tree.root_node)
    except Exception:
        return {"defs": [], "refs": {}}
    if not isinstance(caps, dict):
        return {"defs": [], "refs": {}}
    defs, refs = _process_captures(caps, data.split(b"\n"))
    return {"defs": defs, "refs": refs}


# --- file discovery --------------------------------------------------------


def list_files(root: Path, max_files: int) -> list[Path]:
    """Tracked source files via `git ls-files`, else a filtered walk."""
    rels: list[str] = []
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, timeout=30, check=True,
        )
        rels = [ln for ln in out.stdout.splitlines() if ln.strip()]
    except (subprocess.SubprocessError, OSError):
        rels = []

    paths: list[Path] = []
    if rels:
        for rel in rels:
            p = root / rel
            if p.suffix in LANG_BY_EXT and not p.is_symlink():
                paths.append(p)
    else:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix in LANG_BY_EXT and not p.is_symlink():
                    paths.append(p)
    return paths[:max_files]


# --- mtime cache -----------------------------------------------------------


def cache_path(root: Path) -> Path:
    digest = hashlib.sha1(str(root.resolve()).encode()).hexdigest()[:16]
    return Path.home() / ".claude" / "data" / "repo-map-cache" / f"{digest}.json"


def load_cache(root: Path, use_cache: bool) -> dict:
    if not use_cache:
        return {}
    try:
        raw = json.loads(cache_path(root).read_text(encoding="utf-8"))
        if raw.get("version") == CACHE_VERSION:
            return raw.get("files", {})
    except (OSError, ValueError):
        pass
    return {}


def save_cache(root: Path, files: dict, use_cache: bool) -> None:
    if not use_cache:
        return
    try:
        cp = cache_path(root)
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(
            json.dumps({"version": CACHE_VERSION, "files": files}),
            encoding="utf-8",
        )
    except OSError:
        pass


# --- graph + PageRank (self-contained; no numpy/scipy/networkx) ------------


def pagerank(
    nodes: list[str],
    edges: list[tuple[str, str, float]],
    personalization: dict[str, float] | None = None,
    damping: float = PAGERANK_DAMPING,
    iters: int = PAGERANK_ITERS,
) -> dict[str, float]:
    """Weighted PageRank via power iteration, with a personalization teleport
    vector and dangling-node redistribution. Mirrors networkx semantics."""
    n = len(nodes)
    if n == 0:
        return {}
    out_weight: dict[str, float] = {x: 0.0 for x in nodes}
    for u, _v, w in edges:
        out_weight[u] += w
    dangling_nodes = [x for x in nodes if out_weight[x] == 0.0]
    if personalization and sum(personalization.values()) > 0:
        s = sum(personalization.get(x, 0.0) for x in nodes) or 1.0
        teleport = {x: personalization.get(x, 0.0) / s for x in nodes}
    else:
        teleport = {x: 1.0 / n for x in nodes}
    rank = {x: 1.0 / n for x in nodes}
    for _ in range(iters):
        nxt = {x: (1.0 - damping) * teleport[x] for x in nodes}
        dangling = sum(rank[x] for x in dangling_nodes)
        for u, v, w in edges:
            nxt[v] += damping * rank[u] * (w / out_weight[u])
        for x in nodes:
            nxt[x] += damping * dangling * teleport[x]
        delta = sum(abs(nxt[x] - rank[x]) for x in nodes)
        rank = nxt
        if delta < PAGERANK_TOL:
            break
    total = sum(rank.values()) or 1.0
    return {x: rank[x] / total for x in nodes}


def recent_git_files(root: Path) -> set[str]:
    """Files touched in the working tree or the last few commits (personalization
    bias). Empty set if not a git repo."""
    recent: set[str] = set()
    for cmd in (
        ["git", "-C", str(root), "status", "--porcelain"],
        ["git", "-C", str(root), "diff", "--name-only", "HEAD~3..HEAD"],
    ):
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=20, check=True
            )
        except (subprocess.SubprocessError, OSError):
            continue
        for ln in out.stdout.splitlines():
            rel = ln[3:].strip() if cmd[3] == "status" else ln.strip()
            if rel:
                recent.add(rel)
    return recent


# --- orchestration ---------------------------------------------------------


def build_tags(root: Path, files: list[Path], use_cache: bool) -> dict[str, dict]:
    """relpath -> tags, reusing the mtime cache where the file is unchanged."""
    cache = load_cache(root, use_cache)
    fresh: dict[str, dict] = {}
    for path in files:
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_size > DEFAULT_MAX_FILE_BYTES:
            continue
        rel = os.path.relpath(path, root)
        sig = [int(st.st_mtime_ns), st.st_size]
        hit = cache.get(rel)
        if hit and hit.get("sig") == sig:
            fresh[rel] = hit
            continue
        key = LANG_BY_EXT[path.suffix]
        tags = extract_tags(path, key)
        fresh[rel] = {"sig": sig, "defs": tags["defs"], "refs": tags["refs"]}
    save_cache(root, fresh, use_cache)
    return fresh


def _graph_from_tags(
    tags: dict[str, dict],
) -> tuple[list[str], list[tuple[str, str, float]], dict[str, int]]:
    """Build (nodes, edges, global_ref_counts). An edge referencer->definer is
    weighted by how many times the referencer uses names the definer defines
    (aggregated per pair). Ubiquitous names (defined in > MAX_DEFINERS files) are
    skipped for edges — too common to inform centrality — but still scored."""
    definers: dict[str, set[str]] = {}
    global_refs: dict[str, int] = {}
    for rel, t in tags.items():
        for name, _line, _sig in t["defs"]:
            definers.setdefault(name, set()).add(rel)
        for name, count in t["refs"].items():
            global_refs[name] = global_refs.get(name, 0) + count
    agg: dict[tuple[str, str], float] = {}
    for rel, t in tags.items():
        for name, count in t["refs"].items():
            defs_for = definers.get(name)
            if not defs_for or len(defs_for) > MAX_DEFINERS:
                continue
            for definer in defs_for:
                if definer != rel:
                    agg[(rel, definer)] = agg.get((rel, definer), 0.0) + count
    edges = [(u, v, w) for (u, v), w in agg.items()]
    return list(tags.keys()), edges, global_refs


def _personalization(
    nodes: list[str], focus: list[str], recent: set[str]
) -> dict[str, float]:
    """Task-aware teleport vector: bias toward --focus paths and recently touched
    files, so the map orients around what you're working on."""
    focus_set = {os.path.normpath(f) for f in focus}
    vec: dict[str, float] = {}
    for rel in nodes:
        score = 1.0
        if rel in focus_set or os.path.normpath(rel) in focus_set:
            score += 100.0
        if rel in recent:
            score += 10.0
        vec[rel] = score
    return vec


def _relativize_focus(focus: list[str], cwd: Path, root: Path) -> list[str]:
    """Make --focus paths comparable to the tags' root-relative keys: resolve each
    against the original cwd (where the user typed it), then relativize to root.
    Without this, the git-toplevel rewrite of root would silently break --focus
    when invoked from a subdirectory."""
    out: list[str] = []
    for f in focus:
        p = Path(f) if os.path.isabs(f) else (cwd / f)
        try:
            out.append(os.path.relpath(p.resolve(), root))
        except (OSError, ValueError):
            out.append(f)
    return out


def rank_symbols(
    tags: dict[str, dict], focus: list[str], recent: set[str]
) -> list[tuple[str, str, int, str, float]]:
    """Return (relpath, name, line, sig, score) sorted by score desc."""
    nodes, edges, global_refs = _graph_from_tags(tags)
    ranks = pagerank(nodes, edges, _personalization(nodes, focus, recent))
    out: list[tuple[str, str, int, str, float]] = []
    for rel, t in tags.items():
        file_rank = ranks.get(rel, 0.0)
        for name, line, sig in t["defs"]:
            symbol_score = file_rank * (1 + global_refs.get(name, 0))
            out.append((rel, name, line, sig, symbol_score))
    out.sort(key=lambda r: (-r[4], r[0], r[2]))
    return out


def render(
    ranked: list[tuple[str, str, int, str, float]],
    root: Path,
    budget_tokens: int,
    total_symbols: int,
) -> str:
    chosen: list[tuple[str, str, int, str, float]] = []
    used = 0
    for row in ranked:
        _rel, _name, line, sig, _score = row
        cost = max(1, len((f"  {line}: {sig}")) // 4)
        if used + cost > budget_tokens and chosen:
            break
        chosen.append(row)
        used += cost

    by_file: dict[str, list[tuple[int, str]]] = {}
    file_order: list[str] = []
    best_rank: dict[str, float] = {}
    seen_lines: dict[str, set[int]] = {}
    for rel, _name, line, sig, score in chosen:
        if rel not in by_file:
            by_file[rel] = []
            file_order.append(rel)
            seen_lines[rel] = set()
        if line not in seen_lines[rel]:  # collapse multiple defs on one line
            seen_lines[rel].add(line)
            by_file[rel].append((line, sig))
        best_rank[rel] = max(best_rank.get(rel, 0.0), score)
    file_order.sort(key=lambda r: (-best_rank[r], r))

    # Count + token total reflect the lines actually emitted (after collapsing
    # multiple defs that share a source line), so the header matches the body.
    shown = sum(len(v) for v in by_file.values())
    emitted_tokens = sum(
        max(1, len(f"  {line}: {sig}") // 4)
        for v in by_file.values()
        for line, sig in v
    )
    head = [
        f"# Repo map — {root} ({shown} of {total_symbols} symbols, "
        f"~{emitted_tokens} tokens)",
        "#",
        "# Ranked orientation map (tree-sitter tags -> PageRank). Signatures only;",
        "# use serena or Read for full bodies. Higher = more central to the repo.",
        "",
    ]
    body: list[str] = []
    for rel in file_order:
        body.append(rel)
        for line, sig in sorted(by_file[rel]):
            body.append(f"  {line}: {sig}")
    return "\n".join(head + body) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Local repo-map (tree-sitter -> PageRank)."
    )
    ap.add_argument("--root", default=".", help="repo root (default: cwd / git top)")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET_TOKENS,
                    help="approx token budget for the rendered map")
    ap.add_argument("--focus", action="append", default=[],
                    help="bias ranking toward this path (repeatable)")
    ap.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    ap.add_argument("--no-cache", action="store_true", help="ignore the mtime cache")
    args = ap.parse_args(argv)

    cwd = Path.cwd()
    root = Path(args.root).resolve()
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.strip()
        if top:
            root = Path(top)
    except (subprocess.SubprocessError, OSError):
        pass

    if not root.is_dir():
        sys.stderr.write(f"repo-map: not a directory: {root}\n")
        return 1

    try:
        files = list_files(root, args.max_files)
    except OSError as exc:
        sys.stderr.write(f"repo-map: cannot list files: {exc}\n")
        return 1
    if not files:
        print(f"# Repo map — {root}\n#\n# No supported source files "
              "(.py/.js/.jsx/.ts/.tsx) found.")
        return 0

    try:
        get_language(LANG_BY_EXT[files[0].suffix])
    except Exception as exc:  # tree-sitter / grammar import failure
        _fatal_missing(exc)

    tags = build_tags(root, files, use_cache=not args.no_cache)
    total_symbols = sum(len(t["defs"]) for t in tags.values())
    if total_symbols == 0:
        print(f"# Repo map — {root}\n#\n# Parsed {len(files)} file(s); no symbols "
              "extracted.")
        return 0

    recent = recent_git_files(root)
    focus = _relativize_focus(args.focus, cwd, root)
    ranked = rank_symbols(tags, focus, recent)
    print(render(ranked, root, args.budget, total_symbols), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
