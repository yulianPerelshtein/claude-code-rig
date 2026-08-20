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

# A window of 7 let one burst of probe runs fill the corpus; synthetic sessions
# are now excluded BEFORE the window is applied, so this counts real sessions.
DEFAULT_WINDOW = 25
DEFAULT_KEEP = 500  # retention: max session-summary files to keep on disk
DREAM_LOG_MAX_LINES = 2000  # cap dream-loop.log when it grows past ~512 KB
TOP_THEMES = 12
RECURRING_MIN_SESSIONS = 2
SNIPPET_LEN = 200
# A session with almost no exchange carries no lesson; below this it is a probe
# or an aborted start, whether or not anything marked it.
MIN_MESSAGES = 6

# Machine-generated wrappers Claude Code injects into a transcript. Their tag
# names and boilerplate prose were, for a month, the entire theme table: every
# report's top themes were `command-args`, `local-command-caveat`, `generated`
# and friends, because they recur in every session that runs a slash command.
MARKUP_RE = re.compile(r"<[^>]*>")
# A "prompt" that opens with a wrapper tag is not a human prompt at all: it is
# Claude Code injecting the slash-command envelope, a command's stdout, or a
# task notification. 126 of 309 captured prompt bullets were these. Stripping
# the tags alone was not enough — the caveat's own prose ("the messages below
# were generated ... DO NOT respond ... unless") then became the theme table.
WRAPPER_LEAD_RE = re.compile(r"^\s*<[a-z][a-z0-9-]*>")
URL_RE = re.compile(r"https?://\S+")
# Absolute paths tokenise into their segments, which surfaced `home`, the
# username and the employer name as "recurring themes" — noise, and precisely
# the strings the redaction markers exist to keep out of shared text.
PATH_RE = re.compile(r"(?:~|\.{0,2})/[\w.~/-]+")
# Harness notices that appear mid-transcript rather than as a wrapper tag.
NOTICE_RE = re.compile(r"\[(?:request interrupted|[^\]]*interrupted by user)[^\]]*\]",
                       re.IGNORECASE)
# WORD_RE requires >= 4 chars, so only meaningful long tokens are counted.
STOPWORDS = frozenset(
    """
    that this with from have will your you are not but its into over only
    just then them they when what which while none captured user assistant
    session summary first last results
    command commands command-name command-args command-message caveat
    local-command-caveat local task-notification task-id tool-use-id
    output-file system-reminder bash-input bash-stdout bash-stderr status
    stdout stderr asks below consider explicitly generated response
    something these those should would could might must need needs want
    wants right there here like about after before because being other
    than their thing things still also make made does done please thanks
    when where does note only very much many some such into onto
    """.split()
)
WORD_RE = re.compile(r"[a-z][a-z0-9_-]{3,}")
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
        prompts = [
            p for p in first_prompts(text) if not WRAPPER_LEAD_RE.match(p)
        ]
        snippet = prompts[0][:SNIPPET_LEN] if prompts else "(no user prompt captured)"
        entries.append((path.name, snippet))
        text_l = " ".join(prompts).lower()
        for pattern in (MARKUP_RE, NOTICE_RE, URL_RE, PATH_RE):
            text_l = pattern.sub(" ", text_l)
        cleaned = text_l
        words = {w for w in WORD_RE.findall(cleaned) if w not in STOPWORDS}
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
        "ACCEPTed, append a one-line operational rule under an "
        "`## Accepted for distilled.md` section IN THIS REPORT. /weekly-retro "
        "drains it into learnings/distilled.md by draft PR.",
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
    summaries_skipped = 0
    error = ""
    try:
        all_summaries = sorted_summaries()
        summaries, summaries_skipped = real_summaries(all_summaries, window)
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
