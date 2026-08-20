#!/usr/bin/env bash
# capture-hook-payloads.sh [--keep]
#
# Rebuild tests/hooks/fixtures/ from payloads a LIVE session actually emits.
#
# Why this exists: the hook fixtures used to be written by hand, from the same
# assumption as the hook under test. read_injection_scanner.py read a top-level
# `tool_response.content` that neither Read nor WebFetch sends, so it extracted
# the empty string and scanned nothing from its first commit — while ten
# hand-authored tests passed. A fixture is only worth anything if it came off
# the wire.
#
# Captures into a throwaway project dir, SANITISES, then writes the fixtures.
# Raw payloads carry absolute paths (and therefore the username), so they never
# reach the repo; only the sanitised result does.
set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURES="${RIG_DIR}/tests/hooks/fixtures"
KEEP=0
[[ "${1:-}" == "--keep" ]] && KEEP=1

WORK="$(mktemp -d "${TMPDIR:-/tmp}/cc-capture-XXXXXX")"
trap '[[ "${KEEP}" -eq 0 ]] && chmod -R u+w "${WORK}" 2>/dev/null && find "${WORK}" -delete 2>/dev/null' EXIT

command -v claude >/dev/null || { echo "capture: 'claude' not on PATH" >&2; exit 1; }

mkdir -p "${WORK}/.claude"
cat > "${WORK}/dump.py" <<'PY'
import sys, json, os, time
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payloads")
os.makedirs(d, exist_ok=True)
raw = sys.stdin.read()
try:
    name = json.loads(raw).get("tool_name", "unknown")
except Exception:
    name = "unparsed"
open(os.path.join(d, f"{name}-{time.time_ns()}.json"), "w").write(raw)
PY

cat > "${WORK}/.claude/settings.json" <<PY
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Read|WebFetch", "hooks": [{"type": "command", "command": "python3 ${WORK}/dump.py"}]}
    ]
  }
}
PY

printf 'This is an ordinary sample document about widget inventory.\nNothing special here at all.\nJust three plain lines of prose.\n' \
    > "${WORK}/sample.md"

# --allowedTools, not settings.permissions: an untrusted workspace silently
# drops permissions.allow from a project settings.json.
echo "== Capturing Read =="
( cd "${WORK}" && timeout 300 claude -p \
    "Read the file sample.md and tell me how many lines it has. Then stop." \
    --allowedTools "Read" >/dev/null 2>&1 )

echo "== Capturing WebFetch =="
( cd "${WORK}" && timeout 300 claude -p \
    "Use WebFetch on https://example.com with the prompt 'what is the page title'. Then stop." \
    --allowedTools "WebFetch" >/dev/null 2>&1 )

echo "== Sanitising =="
python3 - "${WORK}" "${FIXTURES}" <<'PY'
import glob, json, os, sys

work, fixtures = sys.argv[1], sys.argv[2]
os.makedirs(fixtures, exist_ok=True)

# Every value that identifies the capturing machine is replaced; the STRUCTURE
# is the whole point of the fixture and is left exactly as captured.
SUBS = {
    "session_id": "00000000-0000-4000-8000-000000000001",
    "prompt_id": "00000000-0000-4000-8000-000000000002",
    "tool_use_id": "toolu_00000000000000000000000000",
    "transcript_path": "/home/dev/.claude/projects/-work-sample/session.jsonl",
    "cwd": "/work/sample",
    "duration_ms": 6,
}
SAMPLE_PATH = "/work/sample/sample.md"
SAMPLE_TEXT = (
    "This is an ordinary sample document about widget inventory.\n"
    "Nothing special here at all.\n"
    "Just three plain lines of prose.\n"
)
WEBFETCH_RESULT = (
    'The page title is "Example Domain". The page explains that the domain is '
    "reserved for use in illustrative examples.\n"
)

seen = set()
for path in sorted(glob.glob(os.path.join(work, "payloads", "*.json"))):
    d = json.load(open(path))
    tool = d.get("tool_name")
    if tool in seen or tool not in ("Read", "WebFetch"):
        continue
    seen.add(tool)
    for k, v in SUBS.items():
        if k in d:
            d[k] = v
    if tool == "Read":
        d["tool_input"]["file_path"] = SAMPLE_PATH
        f = d["tool_response"]["file"]
        f["filePath"], f["content"] = SAMPLE_PATH, SAMPLE_TEXT
        f["numLines"] = f["totalLines"] = 3
        name = "posttooluse-read.json"
    else:
        d["tool_response"]["result"] = WEBFETCH_RESULT
        d["tool_response"]["bytes"] = 559
        d["tool_response"]["durationMs"] = 1357
        name = "posttooluse-webfetch.json"
    with open(os.path.join(fixtures, name), "w") as fh:
        json.dump(d, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"   wrote {name}  tool_response keys: {sorted(d['tool_response'])}")

for tool in ("Read", "WebFetch"):
    if tool not in seen:
        print(f"   MISSING: no {tool} payload captured", file=sys.stderr)
        sys.exit(1)
PY
rc=$?
[[ "${rc}" -ne 0 ]] && { echo "capture: incomplete — fixtures NOT fully rebuilt" >&2; exit "${rc}"; }

echo "== Verifying no identifiers leaked =="
CHECK="${RIG_DIR}/.github/scripts/check-redactions.sh"
LIST="${RIG_DIR}/tools/scripts/redaction-patterns.local.txt"
if [[ -x "${CHECK}" && -s "${LIST}" ]]; then
    if REDACTION_PATTERNS_FILE="${LIST}" "${CHECK}" "${FIXTURES}"/*.json >/dev/null 2>&1; then
        echo "   redaction gate clean"
    else
        echo "capture: FIXTURES FAILED THE REDACTION GATE — do not commit them" >&2
        exit 1
    fi
else
    echo "   WARN: redaction gate unavailable; check the fixtures by hand" >&2
fi

echo "Done. Review the diff, then run: uv run --with pytest pytest tests/hooks/ -q"
