"""Outcome-policy hard invariants (the runner-side backstop).

The model produces content; the runner decides what may be written or pushed.
The destructive-command base is loaded from core/hooks/blocked-commands.json —
the SAME blocklist the PreToolUse guardrail enforces — so the two never drift.
On top of that base the runner adds the routine-specific invariants the
interactive guardrail does not carry: no merge, no PR merge, no
--dangerously-skip-permissions.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# core/routines/runner/policy.py -> core/hooks/blocked-commands.json
_BLOCKLIST_JSON = (
    Path(__file__).resolve().parents[2] / "hooks" / "blocked-commands.json"
)

# Routine-specific invariants the interactive guardrail does not carry: a
# scheduled routine must never merge, never merge a PR, and never escalate
# permissions. (push-to-default-branch is handled by assert_push_allowed.)
_ROUTINE_EXTRA_PATTERNS = [
    r"\bgit\s+merge\b",
    r"\bgh\s+pr\s+merge\b",
    r"--dangerously-skip-permissions",
]

# Used only if blocked-commands.json cannot be read (defence in depth — a
# missing file must never silently disable the destructive-command guard).
_FALLBACK_PATTERNS = [
    r"\brm\s+-[a-z]*r[a-z]*f",
    r"\brm\s+[^;&|]*(-[a-z]*r\b|--recursive)[^;&|]*(-[a-z]*f\b|--force)",
    r"git\s+push\s+.*--force",
    r"git\s+push\s+.*-f\b",
    r"git\s+reset\s+--hard",
    *_ROUTINE_EXTRA_PATTERNS,
]


class PolicyError(RuntimeError):
    """Raised when a routine attempts an action the outcome policy forbids."""


def _base_regexes(blocklist_json: Path) -> list[str]:
    try:
        data = json.loads(blocklist_json.read_text(encoding="utf-8"))
        return [p["regex"] for p in data.get("patterns", []) if p.get("regex")]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return list(_FALLBACK_PATTERNS)


@lru_cache(maxsize=8)
def load_blocked_patterns(
    blocklist_json: Path | None = None,
) -> tuple[re.Pattern, ...]:
    """Compile the destructive-command patterns: the shipped guardrail blocklist
    (or a fallback if unreadable) plus the routine-specific extras."""
    path = blocklist_json or _BLOCKLIST_JSON
    regexes = _base_regexes(path)
    for extra in _ROUTINE_EXTRA_PATTERNS:
        if extra not in regexes:
            regexes.append(extra)
    return tuple(re.compile(r) for r in regexes)


def assert_push_allowed(branch: str, default_branch: str) -> None:
    if branch.strip() in {default_branch.strip(), "main", "master"}:
        raise PolicyError(f"refuses to push to default branch ({branch})")


def assert_path_in_target(path, target) -> None:
    p = Path(path).resolve()
    t = Path(target).resolve()
    # Never touch the *deployed* ~/.claude originals (the real HOME), regardless
    # of target. Compared against the actual home dir — not magic path components
    # — so it protects /root and /Users HOMEs and does NOT block a target's own
    # project-local .claude/ directory.
    home_claude = (Path.home() / ".claude").resolve()
    if p == home_claude or home_claude in p.parents:
        raise PolicyError(f"refuses to write to deployed ~/.claude path: {p}")
    if p != t and t not in p.parents:
        raise PolicyError(f"refuses to write outside target: {p} not under {t}")


def assert_command_allowed(cmd: str) -> None:
    for pat in load_blocked_patterns():
        if pat.search(cmd):
            raise PolicyError(f"blocked command (policy): {cmd}")
