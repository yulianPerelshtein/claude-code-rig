#!/usr/bin/env bash
# install-routine-timers.sh [--dry-run] [--include-mutating] [--uninstall]
# Render core/routines/templates/systemd/*.tmpl and install one timer per
# scheduled+enabled routine in registry.yaml.
#
# Without this, a routine can declare `{type: scheduled, on_calendar: ...}` and
# `enabled: true` and never run once — the registry says enabled, systemd has
# never heard of it, and nothing reports the discrepancy. `/routines enable`
# assumed these units already existed.
#
# A `draft-pr` routine pushes a branch and opens a PR unattended, which
# safety-rules.md says needs explicit confirmation. Its unit is written but left
# DISABLED unless --include-mutating is passed; report-only and
# local-write-allowlist routines are enabled by default. Same reasoning as the
# CI substrate being tier-2 opt-in.
#
# Idempotent: re-rendering an unchanged unit is a no-op; changed units are
# rewritten and the timer re-enabled.
set -uo pipefail

RIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPL_DIR="${RIG_DIR}/core/routines/templates/systemd"
UNIT_DIR="${HOME}/.config/systemd/user"
REGISTRY="${RIG_DIR}/core/routines/registry.yaml"

DRY_RUN=0
UNINSTALL=0
INCLUDE_MUTATING=0
MUTATING_OUTCOMES="draft-pr"
for arg in "$@"; do
    case "${arg}" in
        --dry-run)          DRY_RUN=1 ;;
        --uninstall)        UNINSTALL=1 ;;
        --include-mutating) INCLUDE_MUTATING=1 ;;
        -h|--help)          sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "unknown option: ${arg}" >&2; exit 2 ;;
    esac
done

if [[ -t 1 ]]; then
    G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
else
    G=""; Y=""; R=""; N=""
fi
ok()   { printf '%s  OK %s  %s\n' "${G}" "${N}" "$1"; }
warn() { printf '%sWARN %s  %s\n' "${Y}" "${N}" "$1"; }
fail() { printf '%sFAIL %s  %s\n' "${R}" "${N}" "$1"; }

# systemd --user must be reachable; WSL without `systemd=true` in /etc/wsl.conf
# has no user manager, and every systemctl call would fail confusingly.
if ! systemctl --user show-environment >/dev/null 2>&1; then
    warn "no systemd --user session — skipping timer install."
    warn "  On WSL: set [boot] systemd=true in /etc/wsl.conf, then 'wsl --shutdown'."
    exit 0
fi

# "name<TAB>on_calendar<TAB>target_default<TAB>outcome" for scheduled+enabled routines.
scheduled_routines() {
    uv run --quiet --with pyyaml python3 - "${REGISTRY}" <<'PY'
import sys, yaml
reg = yaml.safe_load(open(sys.argv[1])) or {}
for name, spec in (reg.get("routines") or {}).items():
    if not spec.get("enabled", False):
        continue
    for trig in spec.get("triggers", []):
        if trig.get("type") == "scheduled" and trig.get("on_calendar"):
            print("\t".join([
                name,
                trig["on_calendar"],
                spec.get("target_default", "cwd"),
                spec.get("outcome", "report-only"),
            ]))
            break
PY
}

mapfile -t ROUTINES < <(scheduled_routines)
if [[ ${#ROUTINES[@]} -eq 0 ]]; then
    warn "no scheduled+enabled routines in ${REGISTRY}"
    exit 0
fi

if [[ "${UNINSTALL}" -eq 1 ]]; then
    for line in "${ROUTINES[@]}"; do
        name="${line%%$'\t'*}"
        systemctl --user disable --now "cc-routine-${name}.timer" >/dev/null 2>&1
        rm -f "${UNIT_DIR}/cc-routine-${name}.timer"
        ok "removed cc-routine-${name}.timer"
    done
    rm -f "${UNIT_DIR}/cc-routine@.service"
    systemctl --user daemon-reload
    ok "uninstalled; run 'systemctl --user list-timers' to confirm"
    exit 0
fi

[[ "${DRY_RUN}" -eq 1 ]] && echo "(dry-run: nothing will be written)"
mkdir -p "${UNIT_DIR}"

# Write $2 to $1 only when the content differs; echo "changed" if it did.
write_unit() {
    local dest="$1" content="$2"
    if [[ -f "${dest}" ]] && [[ "$(cat "${dest}")" == "${content}" ]]; then
        return 1
    fi
    [[ "${DRY_RUN}" -eq 1 ]] || printf '%s\n' "${content}" > "${dest}"
    return 0
}

# A timer has no meaningful working directory, so a `cwd`-default routine gets
# the rig root as its explicit target rather than whatever cwd systemd happens
# to hand it.
service_body="$(sed -e "s|__RIG_ROOT__|${RIG_DIR}|g" -e "s|__TARGET__|${RIG_DIR}|g" \
    "${TMPL_DIR}/cc-routine@.service.tmpl")"
if write_unit "${UNIT_DIR}/cc-routine@.service" "${service_body}"; then
    ok "rendered cc-routine@.service (rig=${RIG_DIR})"
else
    ok "cc-routine@.service already current"
fi

CHANGED=0
for line in "${ROUTINES[@]}"; do
    # target_default is informational; a timer always targets the rig root (see
    # the __TARGET__ note above), so it is discarded here.
    IFS=$'\t' read -r name on_calendar _ outcome <<< "${line}"
    timer_body="$(sed -e "s|__NAME__|${name}|g" -e "s|__ON_CALENDAR__|${on_calendar}|g" \
        "${TMPL_DIR}/cc-routine-NAME.timer.tmpl")"
    if write_unit "${UNIT_DIR}/cc-routine-${name}.timer" "${timer_body}"; then
        CHANGED=1
        ok "rendered cc-routine-${name}.timer (${on_calendar}, outcome=${outcome})"
    else
        ok "cc-routine-${name}.timer already current"
    fi
done

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo
    echo "dry-run complete; re-run without --dry-run to install."
    exit 0
fi

[[ "${CHANGED}" -eq 1 ]] && systemctl --user daemon-reload

RC=0
HELD_BACK=()
for line in "${ROUTINES[@]}"; do
    # Only the name and outcome matter here; schedule/target were consumed above.
    IFS=$'\t' read -r name _ _ outcome <<< "${line}"
    if [[ " ${MUTATING_OUTCOMES} " == *" ${outcome} "* ]] && [[ "${INCLUDE_MUTATING}" -eq 0 ]]; then
        HELD_BACK+=("${name} (${outcome})")
        warn "cc-routine-${name}.timer installed but NOT enabled — outcome '${outcome}' pushes and opens a PR unattended"
        continue
    fi
    if systemctl --user enable --now "cc-routine-${name}.timer" >/dev/null 2>&1; then
        next="$(systemctl --user show -p NextElapseUSecRealtime --value "cc-routine-${name}.timer" 2>/dev/null)"
        ok "cc-routine-${name}.timer enabled${next:+ (next: ${next})}"
    else
        fail "could not enable cc-routine-${name}.timer"
        RC=1
    fi
done

echo
if [[ ${#HELD_BACK[@]} -gt 0 ]]; then
    echo "Held back (re-run with --include-mutating, or enable one by name):"
    for h in "${HELD_BACK[@]}"; do echo "  - ${h}"; done
    echo "  systemctl --user enable --now cc-routine-<name>.timer"
    echo
fi
echo "Verify:  systemctl --user list-timers 'cc-routine-*'"
exit "${RC}"
