#!/usr/bin/env python3
"""SessionEnd (or cron) consolidation — the "dream loop" (items #3 + #12).

Runs *after* a session ends (or from cron/systemd), reads the recent session
summaries written by session_end.py, and writes a deterministic consolidation
report to ~/.claude/data/dream-reports/<date>.md. It does NO model inference —
it surfaces recurring themes as a scaffold; the /dream-report skill is where the
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

DEFAULT_WINDOW = 7
DEFAULT_KEEP = 500  # retention: max session-summary files to keep on disk
DREAM_LOG_MAX_LINES = 2000  # cap dream-loop.log when it grows past ~512 KB
TOP_THEMES = 12
RECURRING_MIN_SESSIONS = 2
SNIPPET_LEN = 200
# WORD_RE requires >= 4 chars, so only meaningful long tokens are counted; the
# domain words below suppress the session-summary scaffolding from leaking as
# "themes" (e.g. the "- (none captured)" placeholder).
STOPWORDS = frozenset(
    """
    that this with from have will your you are not but its into over only
    just then them they when what which while none captured user assistant
    session summary first last results
    """.split()
)
WORD_RE = re.compile(r"[a-z][a-z0-9_-]{3,}")
BULLET_RE = re.compile(r"^- (.+)$")


def sorted_summaries() -> list[Path]:
    """All session summaries, newest first (single glob + sort)."""
    if not SESSION_SUMMARY_DIR.is_dir():
        return []
    return sorted(
        SESSION_SUMMARY_DIR.glob("*.md"),
        key=lambda p: (p.stat().st_mtime, p.name),
        reverse=True,
    )


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


def aggregate(paths: list[Path]) -> tuple[list[tuple[str, str]], list[tuple[str, int]]]:
    """Return (session entries, recurring themes). An entry is (name, snippet);
    a theme is (word, number_of_sessions_it_appears_in)."""
    entries: list[tuple[str, str]] = []
    doc_freq: dict[str, int] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        prompts = first_prompts(text)
        snippet = prompts[0][:SNIPPET_LEN] if prompts else "(no prompts captured)"
        entries.append((path.name, snippet))
        words = {
            w for w in WORD_RE.findall(" ".join(prompts).lower()) if w not in STOPWORDS
        }
        for w in words:
            doc_freq[w] = doc_freq.get(w, 0) + 1
    themes = sorted(
        ((w, n) for w, n in doc_freq.items() if n >= RECURRING_MIN_SESSIONS),
        key=lambda kv: (-kv[1], kv[0]),
    )[:TOP_THEMES]
    return entries, themes


def render_report(entries: list[tuple[str, str]], themes: list[tuple[str, int]]) -> str:
    lines = [
        f"# Dream report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Consolidated from {len(entries)} recent session summary file(s). "
        "This is a deterministic scaffold — run `/dream-report` to have the model "
        "turn the candidates below into learnings.",
        "",
        "## Sessions reviewed",
        "",
    ]
    lines += [f"- `{name}` — {snippet}" for name, snippet in entries]
    lines += ["", "## Recurring themes (appear in 2+ sessions)", ""]
    if themes:
        lines.append("| Theme | Sessions |")
        lines.append("|---|---|")
        lines += [f"| {word} | {n} |" for word, n in themes]
    else:
        lines.append("_No theme recurred across 2+ sessions in this window._")
    lines += [
        "",
        "## Candidate learnings (review with /dream-report)",
        "",
        "For each recurring theme, decide ACCEPT / DISCARD / MODIFY and, if "
        "ACCEPTed, append a one-line operational rule to `~/.claude/learnings.md` "
        "with a `# from dream-report YYYY-MM-DD` provenance line.",
        "",
    ]
    lines += [f"- [ ] {word} (seen in {n} sessions) — " for word, n in themes]
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
    error = ""
    try:
        all_summaries = sorted_summaries()
        summaries = all_summaries[:window]
        summaries_read = len(summaries)
        if not summaries:
            print("dream_loop: no session summaries yet, skipping", file=sys.stderr)
        else:
            entries, themes = aggregate(summaries)
            patterns_found = len(themes)
            DREAM_REPORT_DIR.mkdir(parents=True, exist_ok=True)
            out = DREAM_REPORT_DIR / f"{datetime.now().strftime('%Y%m%d')}.md"
            out.write_text(render_report(entries, themes), encoding="utf-8")
            report_path = str(out)
            prune_summaries(all_summaries, int_env("CC_SUMMARY_KEEP", DEFAULT_KEEP))
    except Exception as exc:  # never raise from a hook
        error = f"{type(exc).__name__}: {exc}"[:200]
    log_telemetry(
        {
            "ts": datetime.now().isoformat(),
            "trigger": trigger,
            "summaries_read": summaries_read,
            "patterns_found": patterns_found,
            "report_path": report_path,
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
            "error": error,
        }
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
