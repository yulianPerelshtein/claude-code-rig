#!/usr/bin/env python3
"""SessionEnd (or cron) consolidation — the "dream loop" (items #3 + #12).

Runs *after* a session ends (or from cron/systemd), reads the recent session
summaries written by session_end.py, and writes a deterministic consolidation
report to ~/.claude/data/dream-reports/<date>.md. It does NO model inference —
it lists the facts that recur across the reviewed sessions (failure classes,
files edited, skills and agents used; utils/transcript_facts.py reads them from
each session's transcript) as a scaffold; the /dream-report skill is where the
model turns candidates into learnings.

Contract (per ENHANCEMENTS_BACKLOG §7):
  - If ~/.claude/data/session-summaries/ is missing or empty, exit 0 with the
    single stderr line `dream_loop: no session summaries yet, skipping`.
  - Never raises.
  - Appends exactly one JSONL telemetry line per invocation to
    ~/.claude/data/dream-loop.log:
    {ts, trigger, summaries_read, patterns_found, report_path, latency_ms, error}
"""

import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import (  # noqa: E402
    DREAM_LOG,
    DREAM_REPORT_DIR,
    SESSION_SUMMARY_DIR,
)
from utils.hooklib import append_jsonl, int_env, read_payload  # noqa: E402
from utils.transcript_facts import KINDS, session_facts  # noqa: E402

# A window of 7 let one burst of probe runs fill the corpus; synthetic sessions
# are now excluded BEFORE the window is applied, so this counts real sessions.
DEFAULT_WINDOW = 25
DEFAULT_KEEP = 500  # retention: max session-summary files to keep on disk
DREAM_LOG_MAX_LINES = 2000  # cap dream-loop.log when it grows past ~512 KB
TOP_FACTS = 10  # per kind
RECURRING_MIN_SESSIONS = 2
SNIPPET_LEN = 200
# A session with almost no exchange carries no lesson; below this it is a probe
# or an aborted start, whether or not anything marked it.
MIN_MESSAGES = 6

# A "prompt" that opens with a wrapper tag is not a human prompt at all: it is
# Claude Code injecting the slash-command envelope, a command's stdout, or a
# task notification. 126 of 309 captured prompt bullets were these. Stripping
# the tags alone was not enough — the caveat's own prose ("the messages below
# were generated ... DO NOT respond ... unless") then became the theme table.
WRAPPER_LEAD_RE = re.compile(r"^\s*<[a-z][a-z0-9-]*>")
BULLET_RE = re.compile(r"^- (.+)$")
PROJECT_RE = re.compile(r"^- Project:\s*(.+)$", re.MULTILINE)
MESSAGES_RE = re.compile(r"^- Messages with text:\s*(\d+)", re.MULTILINE)
SYNTHETIC_RE = re.compile(r"^- Synthetic:\s*true\s*$", re.MULTILINE | re.IGNORECASE)


def sorted_summaries() -> list[Path]:
    """All session summaries, newest first (single glob + sort)."""
    if not SESSION_SUMMARY_DIR.is_dir():
        return []
    return sorted(
        SESSION_SUMMARY_DIR.glob("*.md"),
        key=lambda p: (p.stat().st_mtime, p.name),
        reverse=True,
    )


def is_synthetic(text: str) -> bool:
    """True for a session that no human drove, so it carries no lesson.

    Three signals, cheapest first: the explicit marker session_end.py writes
    when ``CC_SYNTHETIC_SESSION`` is set; a project directory under a temp dir
    (every harness runs there); and too few messages to contain an exchange.

    This exists because the rig's own ``self-check`` probe spawns a headless
    session daily. Its summaries were 28% of the corpus and, being short and
    identical, dominated every theme table they appeared in.
    """
    if SYNTHETIC_RE.search(text):
        return True
    project = PROJECT_RE.search(text)
    if project:
        path = project.group(1).strip()
        tmp = tempfile.gettempdir().rstrip("/")
        if path.startswith((f"{tmp}/", "/tmp/", "/var/tmp/")):
            return True
    messages = MESSAGES_RE.search(text)
    return bool(messages) and int(messages.group(1)) < MIN_MESSAGES


def real_summaries(paths: list[Path], window: int) -> tuple[list[Path], int]:
    """Newest `window` non-synthetic summaries, plus how many were skipped.

    Filtering happens BEFORE the window: taking the newest N and filtering after
    let a single burst of probe runs empty the window.
    """
    kept: list[Path] = []
    skipped = 0
    for path in paths:
        if len(kept) >= window:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if is_synthetic(text):
            skipped += 1
            continue
        kept.append(path)
    return kept, skipped


def prune_summaries(files: list[Path], keep: int) -> None:
    """Delete summary files beyond the newest `keep` to bound disk + sort cost.
    Guarded — a failed unlink never propagates."""
    for path in files[keep:]:
        try:
            path.unlink()
        except OSError:
            continue


def first_prompts(text: str) -> list[str]:
    """Extract the bullet lines under the '## First prompts' section."""
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## First prompts"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            m = BULLET_RE.match(line)
            if m:
                out.append(m.group(1).strip())
    return out


Fact = tuple[str, str, int, int]  # kind, value, sessions, occurrences


def aggregate(paths: list[Path]) -> tuple[list[tuple[str, str]], list[Fact]]:
    """Return (session entries, recurring facts). An entry is (summary name,
    first-prompt snippet). A fact recurs when it appears in RECURRING_MIN_SESSIONS
    or more sessions; the TOP_FACTS of each kind are kept, most sessions first."""
    entries: list[tuple[str, str]] = []
    sessions: dict[tuple[str, str], int] = {}
    occurrences: dict[tuple[str, str], int] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        prompts = [
            p for p in first_prompts(text) if not WRAPPER_LEAD_RE.match(p)
        ]
        snippet = prompts[0][:SNIPPET_LEN] if prompts else "(no user prompt captured)"
        entries.append((path.name, snippet))
        # Summary names are <YYYYMMDD>-<session id>.md (session_end.py).
        for kind, values in session_facts(path.stem.partition("-")[2]).items():
            for value, count in values.items():
                sessions[(kind, value)] = sessions.get((kind, value), 0) + 1
                occurrences[(kind, value)] = occurrences.get((kind, value), 0) + count
    facts: list[Fact] = []
    for kind in KINDS:
        recurring = sorted(
            (
                (value, n, occurrences[(k, value)])
                for (k, value), n in sessions.items()
                if k == kind and n >= RECURRING_MIN_SESSIONS
            ),
            key=lambda f: (-f[1], -f[2], f[0]),
        )
        facts += [(kind, v, n, o) for v, n, o in recurring[:TOP_FACTS]]
    return entries, facts


FACT_HEADINGS = {
    "failure": "Tool failures",
    "edited": "Files edited",
    "skill": "Skills and commands used",
    "agent": "Subagents used",
}


def render_report(entries: list[tuple[str, str]], facts: list[Fact]) -> str:
    lines = [
        f"# Dream report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Consolidated from {len(entries)} recent session summary file(s) and "
        "their transcripts. This is a deterministic scaffold — run `/dream-report` "
        "to have the model turn the candidates below into learnings.",
        "",
        "## Sessions reviewed",
        "",
    ]
    lines += [f"- `{name}` — {snippet}" for name, snippet in entries]
    lines += ["", "## Recurring facts (appear in 2+ sessions)", ""]
    if not facts:
        lines.append("_No fact recurred across 2+ sessions in this window._")
    for kind in KINDS:
        rows = [(v, n, o) for k, v, n, o in facts if k == kind]
        if not rows:
            continue
        lines += [f"### {FACT_HEADINGS[kind]}", "", "| Fact | Sessions | Times |"]
        lines.append("|---|---|---|")
        lines += [f"| {v.replace('|', '/')} | {n} | {o} |" for v, n, o in rows]
        lines.append("")
    lines += [
        "",
        "## Candidate learnings (review with /dream-report)",
        "",
        "For each recurring fact, decide ACCEPT / DISCARD / MODIFY and, if "
        "ACCEPTed, append a one-line operational rule under an "
        "`## Accepted for distilled.md` section IN THIS REPORT. /weekly-retro "
        "drains it into learnings/distilled.md by draft PR.",
        "",
    ]
    lines += [f"- [ ] {k}: {v} ({n} sessions) — " for k, v, n, _ in facts]
    lines.append("")
    return "\n".join(lines)


def log_telemetry(record: dict) -> None:
    try:
        append_jsonl(DREAM_LOG, record, DREAM_LOG_MAX_LINES)
    except OSError:
        pass


def main() -> None:
    start = time.monotonic()
    payload = read_payload()
    trigger = payload.get("reason") or payload.get("hook_event_name") or "manual"
    window = int_env("CC_DREAM_WINDOW", DEFAULT_WINDOW)
    report_path = ""
    patterns_found = 0
    summaries_read = 0
    summaries_skipped = 0
    error = ""
    try:
        all_summaries = sorted_summaries()
        summaries, summaries_skipped = real_summaries(all_summaries, window)
        summaries_read = len(summaries)
        if not summaries:
            print("dream_loop: no session summaries yet, skipping", file=sys.stderr)
        else:
            entries, facts = aggregate(summaries)
            patterns_found = len(facts)
            DREAM_REPORT_DIR.mkdir(parents=True, exist_ok=True)
            out = DREAM_REPORT_DIR / f"{datetime.now().strftime('%Y%m%d')}.md"
            out.write_text(render_report(entries, facts), encoding="utf-8")
            report_path = str(out)
            prune_summaries(all_summaries, int_env("CC_SUMMARY_KEEP", DEFAULT_KEEP))
    except Exception as exc:  # never raise from a hook
        error = f"{type(exc).__name__}: {exc}"[:200]
    log_telemetry(
        {
            "ts": datetime.now().isoformat(),
            "trigger": trigger,
            "summaries_read": summaries_read,
            "summaries_skipped": summaries_skipped,
            "patterns_found": patterns_found,
            "report_path": report_path,
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
            "error": error,
        }
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
