#!/usr/bin/env python3
"""Find native auto-memories that should be rig rules, and ones the rig already covers.

Auto memory is per-repository by design; the rig is cross-repo by design; nothing
connected them. So a preference learned in one repo stayed invisible from every
other one — a "keep docstrings short" note was recorded in one project on
2026-08-04 and still did not fire on a different project's PR nine days later,
because memory does not travel. Meanwhile the same commit-message rule had been
written out twice, once per repo, which is duplication the rig is supposed to
absorb.

This reports both directions:

  DUPLICATED  the same slug in two or more live projects — decided mechanically
  CANDIDATES  `type: feedback`/`user`, i.e. guidance that does not stop at a repo

It deliberately does NOT decide whether the rig already carries a rule. That is
semantic, and word overlap answers it wrongly — it cited a mutation-testing
memory to a PR-hygiene doc at 85%. So this establishes only what is mechanical
and leaves the judgement to `/weekly-retro`, which can read the files and
package accepted items into a draft PR. Writing Layer 1 unattended is not a
thing a detector should do.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RIG_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_DIR = Path(os.path.expanduser("~/.claude"))
PROJECTS_DIR = CLAUDE_DIR / "projects"
REPORT_DIR = CLAUDE_DIR / "data" / "memory-promotion"
# Verdicts already reached, so a judged memory stops resurfacing every week.
DECISIONS = REPORT_DIR / "decisions.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FIELD_RE = r"^\s*{}:\s*[\"']?(.+?)[\"']?\s*$"
WORD_RE = re.compile(r"[a-z][a-z0-9-]{3,}")

# Cross-cutting by definition; `project` and `reference` are local by definition.
PROMOTABLE_TYPES = {"feedback", "user"}
STOPWORDS = {
    "that", "this", "with", "from", "then", "than", "when", "into", "only",
    "must", "never", "always", "should", "which", "there", "their", "them",
    "what", "have", "been", "were", "will", "would", "could", "about", "some",
    "code", "claude", "user", "file", "files", "rule", "rules", "note", "notes",
}


@dataclass
class Memory:
    project: str
    slug: str
    path: Path
    mtype: str
    description: str

    def terms(self) -> set[str]:
        """Everything distinctive about the memory — used for ranking only."""
        text = f"{self.slug.replace('-', ' ')} {self.description}".lower()
        return {w for w in WORD_RE.findall(text) if w not in STOPWORDS}

    def identity(self) -> set[str]:
        """Just the slug's words — what the memory is ABOUT.

        Coverage is judged on these alone. Description words are shared prose
        ("never", "prefer", "the user wants") that collide with any rig file:
        judging on them cited a mutation-testing memory to a PR-hygiene doc at
        85%. A memory named `mutation-test-the-test` is only covered by a file
        that talks about mutation testing.
        """
        words = WORD_RE.findall(self.slug.replace("-", " "))
        return {w for w in words if w not in STOPWORDS}


def decode_project_dir(name: str, root: Path = Path("/")) -> Path | None:
    """`-home-alice-work-api` -> `/home/alice/work/api`, or None.

    The encoding replaces `/` with `-` and is therefore ambiguous: a component
    may itself contain a hyphen, so `-home-alice-my-project` could be
    `.../my/project` or `.../my-project`. Splitting on every hyphen resolves that
    wrongly and silently drops any project with a hyphen in its path — a real
    project would simply stop being scanned, with nothing reporting it.

    So decode against the filesystem instead: at each level try the longest
    run of tokens that names a directory that exists, and recurse.
    """
    tokens = [t for t in name.lstrip("-").split("-") if t]
    if not tokens:
        return None

    def walk(base: Path, rest: list[str]) -> Path | None:
        if not rest:
            return base
        # Longest first, so `my-project` wins over `my` when both exist.
        for take in range(len(rest), 0, -1):
            candidate = base / "-".join(rest[:take])
            if candidate.is_dir():
                found = walk(candidate, rest[take:])
                if found is not None:
                    return found
        return None

    return walk(root, tokens)


def live_project_dirs() -> list[Path]:
    """Memory dirs whose project directory still exists.

    Throwaway sessions leave memory dirs behind — a headless probe in a temp dir
    gets one — and counting those as projects would invent duplication signal
    out of scratch directories.
    """
    dirs = []
    for memdir in sorted(PROJECTS_DIR.glob("*/memory")):
        if decode_project_dir(memdir.parent.name) is not None:
            dirs.append(memdir)
    return dirs


def field(meta: str, name: str) -> str:
    match = re.search(FIELD_RE.format(name), meta, re.MULTILINE)
    return match.group(1).strip() if match else ""


def load_decisions() -> dict[str, dict]:
    """slug -> {verdict, date, note} for memories already triaged.

    Without this the report is identical every run: the same candidates return
    after being promoted, deliberately left local, or judged already covered. A
    weekly report that repeats last week's answers is one nobody reads by the
    third week.
    """
    try:
        return json.loads(DECISIONS.read_text())
    except Exception:
        return {}


def load_memories() -> list[Memory]:
    memories: list[Memory] = []
    for memdir in live_project_dirs():
        project = memdir.parent.name
        for path in sorted(memdir.glob("*.md")):
            if path.name == "MEMORY.md":
                continue
            match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
            meta = match.group(1) if match else ""
            memories.append(
                Memory(
                    project=project,
                    slug=path.stem,
                    path=path,
                    mtype=field(meta, "type") or "(none)",
                    description=field(meta, "description"),
                )
            )
    return memories


def rig_files() -> dict[str, set[str]]:
    """Per-file word sets for Layer 1 and the domain knowledge files.

    Kept per-file rather than as one blob so a coverage claim can name the file
    that supports it. A bare percentage is not evidence, and acting on one would
    mean deleting a memory because the rig happens to share its vocabulary.
    """
    corpus: dict[str, set[str]] = {}
    sources = list((RIG_ROOT / "core").glob("*.md"))
    sources += list((RIG_ROOT / "domains").rglob("*.md"))
    for path in sources:
        try:
            text = path.read_text(encoding="utf-8").lower()
        except OSError:
            continue
        corpus[str(path.relative_to(RIG_ROOT))] = set(WORD_RE.findall(text)) - STOPWORDS
    return corpus


def distinctive(ident: set[str], corpus: dict[str, set[str]]) -> set[str]:
    """Identity terms that actually say what a memory is about.

    A word in most rig files carries no topic information: `user-working-style`
    scored 100% "covered" by context-architecture.md purely on `working` and
    `style`. Dropping ubiquitous terms is plain inverse document frequency, and
    beats extending a stopword list one false positive at a time.
    """
    if not corpus:
        return ident
    limit = max(1, len(corpus) // 4)
    return {t for t in ident if sum(t in words for words in corpus.values()) <= limit}


def coverage(memory: Memory, corpus: dict[str, set[str]]) -> tuple[float, str]:
    """(best single-file coverage of the memory's identity, that file).

    Single-file, not whole-corpus: a rule is carried by SOME file or it is not
    carried. Summing across the rig lets unrelated files lend each other terms.
    """
    ident = distinctive(memory.identity(), corpus)
    if not ident:
        # Nothing distinctive left to match on; claiming coverage would be a
        # guess, and the costly direction of a wrong guess is deleting a memory.
        return 0.0, ""
    best_file, best_score = "", 0.0
    for name, words in corpus.items():
        score = len(ident & words) / len(ident)
        if score > best_score:
            best_file, best_score = name, score
    return best_score, best_file


def classify(
    memories: list[Memory],
    corpus: dict[str, set[str]],
    decided: dict[str, dict] | None = None,
) -> dict[str, list[tuple]]:
    """Split memories into what can be decided mechanically, and what cannot.

    There is deliberately NO "already covered, go trim it" bucket. Deciding
    whether the rig carries a rule is a semantic question, and bag-of-words
    answers it wrongly: successive attempts cited a mutation-testing memory to a
    PR-hygiene doc, then rated `user-working-style` fully covered by
    context-architecture.md on the words "working" and "style". Tightening the
    threshold moved which items were wrong, not how many. So this reports the
    two things it can establish — the same slug in two projects, and the
    schema's own cross-cutting `type` — and hands the judgement to
    `/weekly-retro`, which can actually read the file.
    """
    by_slug: dict[str, list[Memory]] = defaultdict(list)
    for memory in memories:
        by_slug[memory.slug].append(memory)

    decided = load_decisions() if decided is None else decided
    buckets: dict[str, list[tuple]] = {
        "duplicated": [], "candidates": [], "settled": [],
    }
    for slug, group in sorted(by_slug.items()):
        if not any(m.mtype in PROMOTABLE_TYPES for m in group):
            continue
        _, nearest = coverage(group[0], corpus)
        if slug in decided:
            buckets["settled"].append((slug, group, decided[slug]))
        elif len(group) > 1:
            buckets["duplicated"].append((slug, group, nearest))
        else:
            buckets["candidates"].append((slug, group, nearest))
    return buckets


def short(project: str) -> str:
    return project.lstrip("-").replace("home-yulian-", "").replace("home-yulian", "~")


def _section(title: str, blurb: list[str], rows: list[str]) -> list[str]:
    """One report section, or nothing when it has no rows."""
    if not rows:
        return []
    return ["", f"## {title}", ""] + blurb + [""] + rows


def _rows_duplicated(rows: list[tuple]) -> list[str]:
    out = []
    for slug, group, nearest in rows:
        where = ", ".join(short(m.project) for m in group)
        out.append(f"- **{slug}** — in {where}")
        out.append(f"  - {group[0].description or '(no description)'}")
        if nearest:
            out.append(f"  - nearest: `{nearest}`")
    return out


def _rows_candidates(rows: list[tuple]) -> list[str]:
    out = []
    for slug, group, nearest in rows:
        out.append(f"- **{slug}** ({short(group[0].project)})")
        out.append(f"  - {group[0].description or '(no description)'}")
        if nearest:
            out.append(f"  - nearest: `{nearest}`")
    return out


def _rows_settled(rows: list[tuple]) -> list[str]:
    out = []
    for slug, _group, verdict in rows:
        label = verdict.get("verdict", "?")
        out.append(f"- `{slug}` — **{label}** ({verdict.get('date', '?')})")
        if verdict.get("note"):
            out.append(f"  - {verdict['note']}")
    return out


def render(memories: list[Memory], buckets: dict[str, list[tuple]]) -> str:
    projects = len({m.project for m in memories})
    lines = [
        f"# memory -> rig promotion — {date.today().isoformat()}",
        "",
        f"{len(memories)} memories across {projects} live project(s). "
        f"{len(buckets['duplicated'])} duplicated, "
        f"{len(buckets['candidates'])} undecided candidate(s), "
        f"{len(buckets['settled'])} already judged.",
        "",
        "Auto memory is per-repository; the rig is cross-repo; nothing carries a",
        "rule from one to the other. These are the memories that may need to move.",
        "",
        "`nearest` is the rig file sharing the most vocabulary — a place to start",
        "reading, NOT a claim the rule is already there. Judging coverage by word",
        "overlap is unreliable, so nothing here recommends deleting anything.",
    ]
    lines += _section(
        "Recorded in more than one project",
        ["The same rule written out once per repo is duplication the rig exists",
         "to absorb, and the only signal here that needs no judgement."],
        _rows_duplicated(buckets["duplicated"]),
    )
    lines += _section(
        "Cross-cutting guidance held in one project",
        ["`type: feedback`/`user` is the schema's own word for guidance on how to",
         "work — which does not stop at a repo boundary. Each needs a human call:",
         "promote, leave, or already there."],
        _rows_candidates(buckets["candidates"]),
    )
    lines += _section(
        "Already judged — no action",
        ["Recorded in `decisions.json` by a previous pass. Listed for audit, not",
         "for re-triage: repeating last week's answers is how a weekly report",
         "stops being read."],
        _rows_settled(buckets["settled"]),
    )
    if not (buckets["duplicated"] or buckets["candidates"]):
        lines += ["", "**Nothing new to judge.**"]
    return "\n".join(lines) + "\n"


def main() -> int:
    memories = load_memories()
    buckets = classify(memories, rig_files())
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"{date.today().isoformat()}.md"
    report.write_text(render(memories, buckets))
    (REPORT_DIR / "latest.json").write_text(
        json.dumps(
            {
                "date": date.today().isoformat(),
                "counts": {name: len(rows) for name, rows in buckets.items()},
                "duplicated": [row[0] for row in buckets["duplicated"]],
                "candidates": [row[0] for row in buckets["candidates"]],
                "settled": [row[0] for row in buckets["settled"]],
            },
            indent=2,
        )
        + "\n"
    )
    print(render(memories, buckets))
    print(f"report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
