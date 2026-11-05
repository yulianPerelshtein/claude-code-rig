"""Deterministic facts about one Claude Code session, read from its transcript.

A fact is a (kind, value) pair that can recur across sessions: a skill or agent
used, a file edited, or a class of tool failure. The dream loop counts in how many
sessions each fact appears; facts in two or more are the candidates /dream-report
turns into rules. Values are normalized so the same thing reads the same in every
session: a file edited from a worktree and from the main checkout is one file, and
a failure message loses its paths, ids and numbers.
"""

import json
import re
from pathlib import Path

from utils.transcript_usage import transcript_files

KINDS = ("failure", "edited", "skill", "agent")
EDIT_TOOLS = frozenset({"Edit", "Write", "NotebookEdit", "MultiEdit"})
# Slash commands that drive the harness rather than run a skill.
BUILTIN_COMMANDS = frozenset(
    """
    add-dir agents clear compact config context cost doctor effort exit fast help
    hooks ide init login logout mcp memory model permissions plugin rename
    rc reload-plugins remote-control resume rewind status statusline usage vim
    """.split()
)
COMMAND_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
WORKTREE_RE = re.compile(r"/\.claude-worktrees/([^/]+)/[^/]+/(.+)$")
TAG_RE = re.compile(r"</?[a-z_-]+>")
BRACKET_RE = re.compile(r"\[[^\]]*\]")
PATH_RE = re.compile(r"(?:~|/)[\w.~@+-]*(?:/[\w.~@+-]+)+")
ID_RE = re.compile(r"\b[0-9a-f]{12,}\b|\b[0-9a-f-]{36}\b")
NUM_RE = re.compile(r"\b\d+\b")
WS_RE = re.compile(r"\s+")
REJECTED = ("doesn't want to proceed", "doesn't want to take this action")
CLASSIFIER = "denied by the claude code auto mode classifier"
MAX_FAILURE_LEN = 90


def failure_class(tool: str, message: str) -> str:
    """'<tool>: <first line of the error>' with paths, ids and numbers masked.

    A shell exit code is kept, since it names the kind of failure."""
    first = next((ln for ln in message.strip().splitlines() if ln.strip()), "")
    lowered = first.lower()
    if any(marker in lowered for marker in REJECTED):
        return f"{tool}: rejected by the user"
    if CLASSIFIER in lowered:
        return f"{tool}: denied by the auto-mode classifier"
    if first.startswith("Exit code "):
        return f"{tool}: {first.strip()}"
    text = TAG_RE.sub("", first)
    text = BRACKET_RE.sub("", text)
    text = PATH_RE.sub("<path>", text)
    text = ID_RE.sub("<id>", text)
    text = NUM_RE.sub("N", text)
    text = WS_RE.sub(" ", text).strip(" :")
    return f"{tool}: {text[:MAX_FAILURE_LEN]}"


def _git_root(path: Path, cache: dict[Path, Path | None]) -> Path | None:
    for parent in path.parents:
        if parent in cache:
            return cache[parent]
        if (parent / ".git").exists():
            cache[parent] = parent
            return parent
    return None


def edited_file(raw: str, cache: dict[Path, Path | None]) -> str | None:
    """'<repo>/<path in repo>' for an edited file, or None for Claude Code's own
    files (its config, plans, memory and scratchpad are not the work)."""
    if "/.claude/" in raw or raw.startswith("/tmp/claude-"):
        return None
    worktree = WORKTREE_RE.search(raw)
    if worktree:
        return f"{worktree.group(1)}/{worktree.group(2)}"
    path = Path(raw)
    root = _git_root(path, cache)
    if root is None:
        return raw
    return f"{root.name}/{path.relative_to(root)}"


def _blocks(rec: dict) -> list[dict]:
    msg = rec.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict)]


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content if isinstance(b, dict)
        )
    return ""


def _commands(text: str) -> list[tuple[str, str]]:
    """Skill facts for the slash commands typed in one message's text."""
    return [
        ("skill", c) for c in COMMAND_RE.findall(text) if c not in BUILTIN_COMMANDS
    ]


def _use_fact(block: dict, roots: dict[Path, Path | None]) -> tuple[str, str] | None:
    name, args = block.get("name"), block.get("input") or {}
    if not isinstance(args, dict):
        return None
    if name == "Skill" and args.get("skill"):
        return ("skill", str(args["skill"]))
    if name in ("Agent", "Task"):
        return ("agent", str(args.get("subagent_type") or "general-purpose"))
    if name in EDIT_TOOLS and args.get("file_path"):
        target = edited_file(str(args["file_path"]), roots)
        return ("edited", target) if target else None
    return None


def _record_facts(
    rec: dict, tools: dict[str, str], roots: dict[Path, Path | None]
) -> list[tuple[str, str]]:
    """The facts in one transcript record. tools maps each tool_use id seen so far
    to its tool name, so a later error result can name the tool that failed."""
    msg = rec.get("message")
    found = []
    if isinstance(msg, dict) and isinstance(msg.get("content"), str):
        found += _commands(msg["content"])
    for block in _blocks(rec):
        kind = block.get("type")
        if kind == "tool_use":
            tools[str(block.get("id"))] = str(block.get("name"))
            fact = _use_fact(block, roots)
            found += [fact] if fact else []
        elif kind == "tool_result" and block.get("is_error"):
            tool = tools.get(str(block.get("tool_use_id")), "?")
            found.append(("failure", failure_class(tool, _text(block.get("content")))))
        elif kind == "text":
            found += _commands(block.get("text", ""))
    return found


def _records(path: Path):
    """Parsed transcript records that can hold a fact; bad lines skipped."""
    try:
        fh = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            if "tool_use" not in line and "<command-name>" not in line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(rec, dict):
                yield rec


def session_facts(session_id: str) -> dict[str, dict[str, int]]:
    """kind -> {fact: occurrences} for one session's main transcript.

    Empty when the session has no transcript left (cleaned up, or another
    machine). Subagent transcripts are not read: their failures are the agent's
    own and would double-count what the main thread already reports."""
    facts: dict[str, dict[str, int]] = {kind: {} for kind in KINDS}
    tools: dict[str, str] = {}
    roots: dict[Path, Path | None] = {}
    for _, path, is_main in transcript_files({session_id}):
        if not is_main:
            continue
        for rec in _records(path):
            for kind, value in _record_facts(rec, tools, roots):
                facts[kind][value] = facts[kind].get(value, 0) + 1
    return facts
