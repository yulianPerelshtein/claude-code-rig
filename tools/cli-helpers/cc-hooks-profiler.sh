#!/usr/bin/env bash
# cc-hooks-profiler.sh [runs] — measure per-hook latency.
# Feeds a minimal JSON payload to each .py/.sh hook under core/hooks/ N times
# (default 20) and reports median + p95 in ms. Target: p95 <= 30 ms (R4).
# Read-only: hooks are invoked with a benign sample payload.
set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS_DIR="${RIG_DIR}/core/hooks"
RUNS="${1:-20}"
SAMPLE='{"tool_name":"Bash","tool_input":{"command":"ls"},"session_id":"profile","cwd":"/tmp"}'

if [[ ! -d "${HOOKS_DIR}" ]]; then
    echo "no core/hooks directory" >&2
    exit 1
fi

printf '%-46s %8s %8s\n' "hook" "med(ms)" "p95(ms)"
printf '%-46s %8s %8s\n' "----" "-------" "-------"

while IFS= read -r -d '' hook; do
    case "${hook}" in
        */utils/*|*/validators/*) continue ;;   # libraries / CLI-invoked, not event hooks
    esac
    case "${hook}" in
        *.py) cmd=(python3 "${hook}") ;;
        *.sh) cmd=(bash "${hook}") ;;
        *) continue ;;
    esac

    times=()
    for ((i = 0; i < RUNS; i++)); do
        start=$(date +%s%N)
        printf '%s' "${SAMPLE}" | "${cmd[@]}" >/dev/null 2>&1 || true
        end=$(date +%s%N)
        times+=("$(( (end - start) / 1000000 ))")
    done

    # median + p95 via sorted array
    mapfile -t sorted < <(printf '%s\n' "${times[@]}" | sort -n)
    n="${#sorted[@]}"
    med="${sorted[$(( n / 2 ))]}"
    p95="${sorted[$(( (n * 95 - 1) / 100 ))]}"
    rel="${hook#"${HOOKS_DIR}/"}"
    printf '%-46s %8s %8s\n' "${rel}" "${med}" "${p95}"
done < <(find "${HOOKS_DIR}" -type f \( -name '*.py' -o -name '*.sh' \) -print0 | sort -z)
