"""Report-file, append-only log, and run-state writers.

Outcome artifacts are the durable signal for headless routine runs (the F.5
lesson: a WSL notify-send toast is unreliable from systemd/headless contexts —
rely on the log + report files instead).
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

LOG_KEEP_LINES = 2000  # bound log.txt so it never grows unbounded
LOG_MAX_BYTES = 512_000


def _today() -> str:
    return datetime.date.today().isoformat()


def write_report(
    report_dir, routine: str, content: str, date: str | None = None
) -> Path:
    """Write a dated routine report (report-only outcomes)."""
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{date or _today()}-{routine}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _rotate(path: Path) -> None:
    """Cheap stat-then-trim: keep only the last LOG_KEEP_LINES once the file
    grows past LOG_MAX_BYTES. Mirrors hooklib.rotate_jsonl_log's contract so the
    routine log is bounded like every other append-only log in the rig."""
    try:
        if path.stat().st_size < LOG_MAX_BYTES:
            return
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        path.write_text("\n".join(lines[-LOG_KEEP_LINES:]) + "\n", encoding="utf-8")
    except OSError:
        return


def append_log(state_dir, line: str) -> None:
    """Append one timestamped line to the human-readable run log (bounded)."""
    out_dir = Path(state_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / "log.txt"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.datetime.now().isoformat()} {line}\n")
    _rotate(log)


def write_state(
    state_dir,
    routine: str,
    *,
    status: str,
    date: str | None = None,
    artifact: str = "",
) -> None:
    """Upsert the per-routine run-state consumed by /routines status. The write
    is atomic (temp file + os.replace) so a concurrent timer can't observe a
    half-written state.json."""
    out_dir = Path(state_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    state[routine] = {"status": status, "date": date or _today(), "artifact": artifact}
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, state_path)
