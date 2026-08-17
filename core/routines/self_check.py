#!/usr/bin/env python3
"""Assert the rig's behaviour, not its file layout.

Every check here exists because the corresponding guarantee failed silently
while every structural check passed: Layer 1 was declared always-loaded and
reached zero sessions; three routines read `enabled: true` and had no systemd
units; the units, once installed, exited 127 nightly; CI's linter was unpinned
and changed verdict on unchanged code. In each case the files were present and
correct — nothing asserted they did anything.

So a check earns its place here only if it observes an EFFECT. `validate.sh`
covers presence; this covers behaviour.

Run: `core/routines/run-routine.sh self-check` (or this script directly).
Writes `~/.claude/data/self-check/<date>.md` plus `latest.json`, and exits
non-zero if any check FAILED. Set `CC_SELFCHECK_NO_LLM=1` to skip the one check
that spawns a headless session.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RIG_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_DIR = Path(os.path.expanduser("~/.claude"))
REPORT_DIR = CLAUDE_DIR / "data" / "self-check"
UNIT_DIR = Path(os.path.expanduser("~/.config/systemd/user"))
INSTALLED_PLUGINS = CLAUDE_DIR / "plugins" / "installed_plugins.json"
PLUGIN_KEY = "claude-code-rig@claude-code-rig"

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

# Claude Code honours @imports anywhere outside code spans and fences, not just
# at line start — CLAUDE.base.md writes its siblings as `- @safety-rules.md`.
# The lookbehind keeps e-mail addresses (`user@host`) out; the char class stops
# at punctuation so `(see @reasoning-preferences.md)` yields a clean path.
IMPORT_RE = re.compile(r"(?<![A-Za-z0-9_.\-/])@([^\s'\"()\[\],;:]+)")
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
CODE_SPAN_RE = re.compile(r"`[^`]*`")
# `uv tool install X`, `npm install -g X`, `pip install X` with no version pin.
UNPINNED_RE = re.compile(
    r"(uv tool install|npm install -g|npm i -g|pipx install|pip install)"
    r"\s+([A-Za-z0-9._-]+)\s*$",
    re.MULTILINE,
)
# Runtime state Claude Code writes INTO the plugin cache; not shipped content.
# `.in_use` must be matched as a path part, not a filename: entries are
# `.in_use/<pid>`, and matching by name let one through as a false positive.
RUNTIME_DIRS = {
    ".git", "__pycache__", ".ruff_cache", ".pytest_cache", ".venv", ".in_use",
}
RUNTIME_FILES = {".gcs-sha", ".DS_Store"}
# Paths the plugin actually ships (see .claude-plugin/plugin.json). Kept in step
# with install/sync-rig.sh, which gates version bumps on the same set.
DELIVERED = ("core", "domains", "skills", ".mcp.json", ".lsp.json", ".claude-plugin")
# SHAs that must no longer be retrievable from the public remote. Kept in a
# GITIGNORED file: published, the list is a map of exactly what to go and fetch.
PURGED_SHAS = RIG_ROOT / "tools" / "scripts" / "purged-shas.local.txt"
PUBLIC_REPO = "yulianPerelshtein/claude-code-rig"
# 404 = repo absent; 422 = "No commit found for SHA" on the commits endpoint.
GONE_CODES = {"404", "422"}


@dataclass
class CheckResult:
    """One assertion's verdict. `evidence` is what a human would need to act."""

    name: str
    status: str
    summary: str
    evidence: list[str] = field(default_factory=list)


def ok(name: str, summary: str, evidence: list[str] | None = None) -> CheckResult:
    return CheckResult(name, PASS, summary, evidence or [])


def bad(name: str, summary: str, evidence: list[str] | None = None) -> CheckResult:
    return CheckResult(name, FAIL, summary, evidence or [])


def skip(name: str, summary: str) -> CheckResult:
    return CheckResult(name, SKIP, summary)


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, **kw)


def probe_payload(command: str) -> str:
    """A PreToolUse Bash hook payload carrying one probe command."""
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def strip_code(text: str) -> str:
    """Ignore fenced blocks and code spans, as Claude Code's import parser does."""
    return CODE_SPAN_RE.sub("", FENCE_RE.sub("", text))


def import_closure(entry: Path) -> tuple[set[Path], list[str]]:
    """(files Claude Code loads from `entry`, imports that resolve to nothing).

    Relative imports resolve against the importing file's directory; the
    documented maximum depth is four hops. A dangling import is returned rather
    than dropped — silently shrinking the expected set is how this check would
    pass while Layer 1 was half-loaded.
    """
    seen: set[Path] = set()
    broken: list[str] = []
    frontier = [(entry, 0)]
    while frontier:
        path, depth = frontier.pop()
        path = path.resolve()
        if path in seen or depth > 4:
            continue
        if not path.is_file():
            broken.append(str(path))
            continue
        seen.add(path)
        for raw in IMPORT_RE.findall(strip_code(path.read_text(encoding="utf-8"))):
            # Only path-shaped tokens; an `@mention` in prose is not an import.
            if not (raw.endswith(".md") or "/" in raw):
                continue
            target = Path(os.path.expanduser(raw))
            if not target.is_absolute():
                target = path.parent / target
            frontier.append((target, depth + 1))
    return seen, broken


def plugin_root() -> tuple[Path | None, str]:
    """(installed plugin dir, recorded commit sha) from installed_plugins.json."""
    try:
        data = json.loads(INSTALLED_PLUGINS.read_text())
        entry = data["plugins"][PLUGIN_KEY][0]
        return Path(entry["installPath"]), entry.get("gitCommitSha", "")
    except Exception:
        return None, ""


# ── Checks ────────────────────────────────────────────────────────────────────


def _layer1_blockers(name: str, entry: Path) -> CheckResult | None:
    """Why the Layer-1 probe cannot run, or None to proceed."""
    if not entry.is_file():
        return bad(name, "~/.claude/CLAUDE.md does not exist — Layer 1 cannot load")
    if os.environ.get("CC_SELFCHECK_NO_LLM"):
        return skip(name, "CC_SELFCHECK_NO_LLM set")
    path_dirs = os.environ.get("PATH", "").split(":")
    if not any((Path(d) / "claude").exists() for d in path_dirs):
        return skip(name, "claude CLI not on PATH")
    return None


def check_layer1_loads() -> CheckResult:
    """Boot a real session and confirm the Layer-1 chain entered its context.

    Reads the InstructionsLoaded hook's own audit log rather than asking the
    model, so the verdict is a fact rather than a judgement.
    """
    name = "layer1-loads"
    entry = CLAUDE_DIR / "CLAUDE.md"
    blocked = _layer1_blockers(name, entry)
    if blocked:
        return blocked

    expected, broken = import_closure(entry)
    if broken:
        return bad(name, f"{len(broken)} @import(s) resolve to nothing", broken)

    with tempfile.TemporaryDirectory() as tmp:
        probe = run(
            ["claude", "-p", "Reply with the single word: ok. Use no tools."],
            cwd=tmp,
            env={**os.environ, "CLAUDE_PROJECT_DIR": tmp},
            timeout=240,
        )
        log = Path(tmp) / ".claude" / "data" / "logs" / "instructions_loaded.jsonl"
        if not log.is_file():
            return bad(
                name,
                "no InstructionsLoaded audit written — the hook is not firing",
                [f"claude -p exited {probe.returncode}", (probe.stderr or "")[:300]],
            )
        loaded = set()
        for line in log.read_text().splitlines():
            try:
                loaded.add(Path(json.loads(line)["file_path"]).resolve())
            except Exception:
                continue

    missing = sorted(str(p) for p in expected - loaded)
    if missing:
        summary = f"{len(missing)}/{len(expected)} Layer-1 files never loaded"
        return bad(name, summary, missing)
    listing = sorted(str(p) for p in expected)
    return ok(name, f"all {len(expected)} Layer-1 files loaded", listing)


def check_deployed_matches_committed() -> CheckResult:
    """Every file in the RUNNING plugin must exist in the commit it claims.

    The running plugin once held five files whose content was in no commit on
    any branch — a hand-synced snapshot that `claude plugin update` would have
    silently reverted.
    """
    name = "deployed-matches-committed"
    root, sha = plugin_root()
    if root is None or not root.is_dir():
        return skip(name, "plugin not installed from the marketplace")
    ref = sha or "HEAD"
    tree = run(["git", "-C", str(RIG_ROOT), "ls-tree", "-r", ref])
    if tree.returncode != 0:
        return bad(name, f"cannot read rig tree at {ref[:8]}", [tree.stderr.strip()])
    rows = (line.split() for line in tree.stdout.splitlines())
    committed = {parts[2] for parts in rows if len(parts) > 2}

    strays: list[str] = []
    checked = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in RUNTIME_DIRS for part in path.parts):
            continue
        if path.name in RUNTIME_FILES:
            continue
        checked += 1
        hashed = run(["git", "-C", str(RIG_ROOT), "hash-object", str(path)])
        blob = hashed.stdout.strip()
        if blob and blob not in committed:
            strays.append(str(path.relative_to(root)))
    if strays:
        summary = f"{len(strays)}/{checked} deployed files are not in {ref[:8]}"
        return bad(name, summary, strays[:20])
    return ok(name, f"all {checked} deployed files match commit {ref[:8]}")


def _fire_probes(hook: Path, probes: dict) -> list[str]:
    """Probe the guardrail; return one line per probe that behaved wrongly."""
    failures: list[str] = []
    for probe in probes["blocked"]:
        proc = run([sys.executable, str(hook)], input=probe_payload(probe["command"]))
        if proc.returncode != 2:
            cmd = probe["command"][:60]
            failures.append(f"NOT BLOCKED (exit {proc.returncode}): {cmd}")
    for probe in probes["allowed"]:
        proc = run([sys.executable, str(hook)], input=probe_payload(probe["command"]))
        if proc.returncode != 0:
            cmd = probe["command"][:60]
            failures.append(f"FALSE POSITIVE (exit {proc.returncode}): {cmd}")
    return failures


def check_guardrail_blocks() -> CheckResult:
    """Fire probes at the INSTALLED guardrail and require a real block.

    Deliberately runs the deployed hook, not the repo copy: a guardrail that is
    correct in git and stale in the plugin cache protects nothing. The `allowed`
    probes are the false-positive guard — a blocklist that stops real work gets
    turned off, which protects nothing either.
    """
    name = "guardrail-blocks"
    root, _ = plugin_root()
    root = root if root and root.is_dir() else RIG_ROOT
    hook = root / "core" / "hooks" / "pre-tool" / "guardrail.py"
    blocklist = root / "core" / "hooks" / "blocked-commands.json"
    if not hook.is_file() or not blocklist.is_file():
        return bad(name, f"guardrail or blocklist missing under {root}")

    probe_file = RIG_ROOT / "core" / "hooks" / "guardrail-probes.json"
    probes = json.loads(probe_file.read_text())
    patterns = [p["regex"] for p in json.loads(blocklist.read_text())["patterns"]]

    failures = _fire_probes(hook, probes)
    if failures:
        return bad(name, f"{len(failures)} guardrail probe(s) misbehaved", failures)

    # State coverage outright: an uncovered pattern is an untested one, and
    # implying otherwise is the exact failure mode this file exists to catch.
    covered = {p.get("covers") for p in probes["blocked"] if p.get("covers")}
    uncovered = [p for p in patterns if p not in covered]
    n_block, n_allow = len(probes["blocked"]), len(probes["allowed"])
    detail = f"{n_block} block + {n_allow} allow probes passed"
    if uncovered:
        detail += f"; {len(uncovered)}/{len(patterns)} patterns have no probe"
    return ok(name, detail, [f"uncovered: {u}" for u in uncovered])


def check_timers_match_registry() -> CheckResult:
    """A scheduled+enabled routine must have an installed unit.

    Three routines declared a schedule and had no unit file at all; the registry
    was the only place that believed they ran.
    """
    name = "timers-match-registry"
    if run(["systemctl", "--user", "show-environment"]).returncode != 0:
        return skip(name, "no systemd --user session")
    try:
        import yaml  # noqa: PLC0415 — optional dep; the rig declares none

        reg_file = RIG_ROOT / "core" / "routines" / "registry.yaml"
        reg = yaml.safe_load(reg_file.read_text())
    except Exception as exc:
        return skip(name, f"registry unreadable ({exc})")

    problems: list[str] = []
    expected = 0
    for rname, spec in (reg.get("routines") or {}).items():
        scheduled = any(t.get("type") == "scheduled" for t in spec.get("triggers", []))
        if not spec.get("enabled") or not scheduled:
            continue
        expected += 1
        unit = UNIT_DIR / f"cc-routine-{rname}.timer"
        if not unit.is_file():
            problems.append(f"{rname}: no unit (run install/install-routine-timers.sh)")
            continue
        # draft-pr timers ship installed-but-disabled by design; not a problem.
        state = run(["systemctl", "--user", "is-enabled", unit.name]).stdout.strip()
        if state != "enabled" and spec.get("outcome") != "draft-pr":
            shown = state or "unknown"
            problems.append(f"{rname}: unit present but is-enabled={shown}")
    if problems:
        summary = f"{len(problems)}/{expected} scheduled routines inert"
        return bad(name, summary, problems)
    return ok(name, f"all {expected} scheduled routines have installed units")


def statusline_script(command: str) -> Path | None:
    """The script a `statusLine.command` runs, e.g. `bash ~/rig/x/statusline.sh`."""
    for token in command.split():
        if token.endswith(".sh"):
            return Path(os.path.expanduser(token))
    return None


def _statusline_checkout() -> Path | None:
    """The directory the configured statusLine script lives in, if any."""
    try:
        settings = json.loads((CLAUDE_DIR / "settings.json").read_text())
    except Exception:
        return None
    script = statusline_script(settings.get("statusLine", {}).get("command", ""))
    return script.resolve().parent if script else None


def check_delivery_paths_agree() -> CheckResult:
    """The two delivery paths must not drift apart unnoticed.

    Skills, agents and hooks load from the plugin cache; Layer 1 and the
    statusline load straight off a checkout, because Claude Code cannot deliver
    either through a plugin — "A CLAUDE.md file at the plugin root is not loaded
    as project context", and a plugin's settings.json honours only `agent` and
    `subagentStatusLine`. Two paths is therefore a constraint, not a choice. The
    failure this catches is them pointing at different commits, so prose rules
    come from one version of the rig while the hooks enforcing them come from
    another.
    """
    name = "delivery-paths-agree"
    problems: list[str] = []

    _, sha = plugin_root()
    head = run(["git", "-C", str(RIG_ROOT), "rev-parse", "HEAD"]).stdout.strip()
    if sha and head and sha != head:
        # Only commits touching SHIPPED paths matter. A tests-only commit leaves
        # the plugin byte-identical, and reporting that as skew would train the
        # reader to ignore this check — the same way a blocklist that stops real
        # work gets switched off.
        argv = ["git", "-C", str(RIG_ROOT), "rev-list", "--count", f"{sha}..HEAD"]
        ahead = run([*argv, "--", *DELIVERED])
        n = int(ahead.stdout.strip() or 0)
        if n:
            problems.append(
                f"plugin is {n} shipped-content commit(s) behind the checkout "
                f"({sha[:8]} vs {head[:8]}) — run install/sync-rig.sh"
            )

    # Layer 1 loads the WORKING TREE, so uncommitted edits ship to every session
    # while the plugin still serves the last published commit.
    closure, _ = import_closure(CLAUDE_DIR / "CLAUDE.md")
    tracked = [p for p in closure if str(p).startswith(str(RIG_ROOT))]
    if tracked:
        rel = [str(p.relative_to(RIG_ROOT)) for p in tracked]
        dirty = run(["git", "-C", str(RIG_ROOT), "status", "--porcelain", "--", *rel])
        for line in dirty.stdout.splitlines():
            if line.strip():
                problems.append(f"Layer 1 serves uncommitted {line[3:].strip()}")

    # The marketplace clone is a real git checkout a person can edit in place;
    # those edits are invisible to the rig and lost on the next update.
    market = CLAUDE_DIR / "plugins" / "marketplaces" / "claude-code-rig"
    if (market / ".git").exists():
        soiled = run(["git", "-C", str(market), "status", "--porcelain"]).stdout.strip()
        if soiled:
            count = len(soiled.splitlines())
            problems.append(
                f"marketplace clone hand-edited ({count} file(s)) — edits will be lost"
            )

    sl = _statusline_checkout()
    if sl and not str(sl).startswith(str(RIG_ROOT)):
        problems.append(f"statusline loads from {sl}, not the rig checkout")

    if problems:
        return bad(name, f"{len(problems)} delivery-path discrepancy(ies)", problems)
    return ok(name, "plugin, Layer 1 and statusline all match the checkout")


def check_history_purged() -> CheckResult:
    """Orphaned pre-rewrite commits must not still be served by the remote.

    A `filter-repo` + force-push rewrites refs; it does NOT make GitHub drop the
    old objects, which stay fetchable by SHA. The June purge was verified "clean
    across all refs" and was clean locally — while the remote kept serving the
    old snapshot, including the redaction pattern list itself. Refs are the wrong
    layer to assert against; this asks the remote.
    """
    name = "history-purged"
    if not PURGED_SHAS.is_file():
        return skip(name, "no purged-shas.local.txt (nothing declared purged)")
    shas = [
        line.strip()
        for line in PURGED_SHAS.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not shas:
        return skip(name, "purged-shas.local.txt is empty")

    # Authenticated when possible: unauthenticated API allows 60 req/hour, and
    # exhausting it returns 403 — which an earlier version silently counted as
    # "fine", so rate limiting made this check report clean.
    #
    # GONE = 404 (repo absent) or 422, which is what this endpoint returns for an
    # absent commit: {"message": "No commit found for SHA: ..."}. Anything else,
    # including 403, is INCONCLUSIVE and must never read as a pass.
    api = f"repos/{PUBLIC_REPO}/commits/"
    url = f"https://api.github.com/{api}"
    path_dirs = os.environ.get("PATH", "").split(":")
    have_gh = any((Path(d) / "gh").exists() for d in path_dirs)
    served, purged, inconclusive = [], 0, {}
    for sha in shas[:200]:
        if have_gh:
            gh_env = {**os.environ,
                      "GH_CONFIG_DIR": os.path.expanduser("~/.config/gh-personal")}
            probe = run(["gh", "api", "-i", api + sha], env=gh_env)
            head = (probe.stdout or "").splitlines()[:1]
            parts = head[0].split() if head else []
            code = parts[1] if len(parts) > 1 else ""
            if not code:
                code = "404" if "Not Found" in (probe.stderr or "") else ""
        else:
            argv = ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                    "-H", "Authorization:", "--max-time", "15", url + sha]
            code = run(argv).stdout.strip()
        if code == "200":
            served.append(sha)
        elif code in GONE_CODES:
            purged += 1
        else:
            key = code or "no-response"
            inconclusive[key] = inconclusive.get(key, 0) + 1

    if served:
        return bad(
            name,
            f"{len(served)} purged commit(s) still served publicly",
            [f"{s} -> HTTP 200 at {url}{s}" for s in served],
        )
    if inconclusive:
        detail = ", ".join(f"{k}x{v}" for k, v in sorted(inconclusive.items()))
        total = sum(inconclusive.values())
        return skip(name, f"inconclusive for {total} SHA(s) ({detail})")
    return ok(name, f"all {purged} purged commits are gone (404/422)")


def check_ci_tools_pinned() -> CheckResult:
    """An unpinned linter in CI changes verdict on unchanged code.

    `uv tool install ruff` was green in July and reported 159 errors in August
    against the same commit, because ruff shipped new default rules in between.
    """
    name = "ci-tools-pinned"
    workflows = sorted((RIG_ROOT / ".github" / "workflows").glob("*.yml"))
    if not workflows:
        return skip(name, "no workflows")
    unpinned = [
        f"{wf.name}: {m.group(0).strip()}"
        for wf in workflows
        for m in UNPINNED_RE.finditer(wf.read_text())
    ]
    if unpinned:
        return bad(name, f"{len(unpinned)} unpinned tool install(s) in CI", unpinned)
    return ok(name, f"{len(workflows)} workflows pin their tools")


CHECKS = (
    check_layer1_loads,
    check_deployed_matches_committed,
    check_delivery_paths_agree,
    check_guardrail_blocks,
    check_timers_match_registry,
    check_history_purged,
    check_ci_tools_pinned,
)


# ── Report ────────────────────────────────────────────────────────────────────


def render(results: list[CheckResult]) -> str:
    counts = {
        status: sum(1 for r in results if r.status == status)
        for status in (PASS, FAIL, SKIP)
    }
    verdict = FAIL if counts[FAIL] else PASS
    lines = [
        f"# rig self-check — {verdict}",
        "",
        f"{counts[FAIL]} failed, {counts[PASS]} passed, {counts[SKIP]} skipped.",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    lines += [f"| `{r.name}` | {r.status} | {r.summary} |" for r in results]
    for r in results:
        if r.evidence:
            lines += ["", f"## {r.name}", ""] + [f"- `{e}`" for e in r.evidence]
    return "\n".join(lines) + "\n"


def verdict_json(results: list[CheckResult]) -> str:
    """Machine-readable verdict; /begin-work reads this to surface failures."""
    return (
        json.dumps(
            {
                "date": date.today().isoformat(),
                "ok": all(r.status != FAIL for r in results),
                "failed": [r.name for r in results if r.status == FAIL],
                "results": [
                    {"name": r.name, "status": r.status, "summary": r.summary}
                    for r in results
                ],
            },
            indent=2,
        )
        + "\n"
    )


def main() -> int:
    results = [check() for check in CHECKS]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"{date.today().isoformat()}.md"
    report.write_text(render(results))
    (REPORT_DIR / "latest.json").write_text(verdict_json(results))
    print(render(results))
    print(f"report: {report}")
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
