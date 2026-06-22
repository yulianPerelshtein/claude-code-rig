#!/usr/bin/env bash
# Redaction-pattern blocklist check.
#
# Used by both .pre-commit-config.yaml (local pre-commit hook) and
# .github/workflows/secret-scan.yml (CI gate). Exits 1 on any hit.
#
# The real company/vendor/project marker regexes are NOT stored in this public
# repo. They are loaded at runtime from a private source (in priority order):
#   1. $REDACTION_PATTERNS_FILE                       (e.g. CI writes a secret here)
#   2. tools/scripts/redaction-patterns.local.txt     (gitignored local copy)
#   3. tools/scripts/redaction-patterns.txt           (tracked template; placeholders)
# If only the template is available the marker scan is best-effort (it can't leak
# real names); the API-key scan below always runs regardless.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Files passed by pre-commit / by the workflow runner.
files=("$@")

# When called from CI without args, scan everything.
if [ ${#files[@]} -eq 0 ]; then
    mapfile -t files < <(find . \
        \( -name '*.md' -o -name '*.py' -o -name '*.sh' \
           -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' \
           -o -name '*.toml' -o -name '*.cfg' \) \
        -not -path './.git/*' -print)
fi

# Self-exclude the regex source files (they contain patterns as literal
# definitions, not as content leaks).
filtered=()
for f in "${files[@]}"; do
    case "$f" in
        check-redactions.sh|*/check-redactions.sh)  ;;
        secret-scan.yml|*/secret-scan.yml)          ;;
        .pre-commit-config.yaml|*/pre-commit-config.yaml) ;;
        redaction-patterns.txt|*/redaction-patterns.txt) ;;
        redaction-patterns.local.txt|*/redaction-patterns.local.txt) ;;
        *) filtered+=("$f") ;;
    esac
done

if [ ${#filtered[@]} -eq 0 ]; then
    exit 0
fi

# The PreToolUse guardrail legitimately contains the Windows-mount path it
# blocks (/mnt/c/) as an enforced OS-isolation rule, not a content leak. Exempt
# it from the MARKER scan only; the API-key scan still covers it.
marker_files=()
for f in "${filtered[@]}"; do
    case "$f" in
        guardrail.py|*/guardrail.py)  ;;
        *) marker_files+=("$f") ;;
    esac
done

# Resolve the private marker-pattern source.
patterns_file="${REDACTION_PATTERNS_FILE:-}"
if [ -z "$patterns_file" ] && [ -f "$REPO_ROOT/tools/scripts/redaction-patterns.local.txt" ]; then
    patterns_file="$REPO_ROOT/tools/scripts/redaction-patterns.local.txt"
fi
if [ -z "$patterns_file" ] && [ -f "$REPO_ROOT/tools/scripts/redaction-patterns.txt" ]; then
    patterns_file="$REPO_ROOT/tools/scripts/redaction-patterns.txt"
fi

# Build a single alternation from the non-comment, non-blank pattern lines.
marker_re=""
if [ -n "$patterns_file" ] && [ -f "$patterns_file" ]; then
    marker_re="$(grep -vE '^[[:space:]]*#|^[[:space:]]*$' "$patterns_file" | paste -sd '|' -)"
fi

if [ -z "$marker_re" ]; then
    echo "note: no redaction marker patterns available — skipping marker scan."
    echo "      (set REDACTION_PATTERNS_FILE or add redaction-patterns.local.txt)"
elif [ ${#marker_files[@]} -gt 0 ] && grep -REn "$marker_re" "${marker_files[@]}" 2>/dev/null; then
    echo ""
    echo "BLOCKED: redaction-pattern hit. See the private redaction-patterns source."
    exit 1
fi

# Well-known API-key prefixes with key-shaped suffixes (always runs).
key_re='(^|[^A-Za-z0-9])(gsk_[A-Za-z0-9]{40,}|sk-[A-Za-z0-9_-]{40,}|xai-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|glpat-[A-Za-z0-9_-]{20,}|ABSK[A-Za-z0-9+/=]{40,})'

if grep -REn "$key_re" "${filtered[@]}" 2>/dev/null; then
    echo ""
    echo "BLOCKED: API key prefix with key-shaped suffix detected. Rotate, then redact."
    exit 1
fi

exit 0
