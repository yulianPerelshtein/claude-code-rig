#!/usr/bin/env python3
"""Bespoke-installer engine (reserved DLP fallback path).

The normal install path is the marketplace plugin (see install/bootstrap-wsl.sh).
This engine is only used on a machine whose DLP blocks the marketplace/clone.
It resolves a profile -> module list -> concrete (source, target) file pairs via
manifests/install.manifest.yaml, then dry-runs or applies the copy with backups
and an install record at ~/.claude/.installed-from-rig.json.

Run via the bash wrappers (install/install-profile.sh, dry-run.sh, ...), which
invoke it as:  uv run --with pyyaml python3 install/lib/installer.py <cmd> ...

Commands:
  resolve  <profile>                 print resolved (source -> target) pairs
  apply    <profile> [--dry-run]     copy files (default: with backup)
                     [--no-backup] [--force]
  rollback                           restore installed files from the latest backup
  uninstall                          remove installer-managed files

Profile vocabulary: `extends:` (parent-profile union) and
`- enhancement: <id>` (opt-in extras resolved against
manifests/marketplace.yaml#enhancements, with `conflicts_with` checks) are
supported. Enhancement *installs* are DEFERRED user actions — the engine
validates + reports them but never runs an install command, so resolve/apply
(incl. --dry-run) stay safe.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST = REPO / "manifests" / "install.manifest.yaml"
MARKETPLACE = REPO / "manifests" / "marketplace.yaml"
HOME = Path(os.path.expanduser("~"))
RECORD = HOME / ".claude" / ".installed-from-rig.json"


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def profile_data(profile: str) -> dict:
    path = REPO / "profiles" / f"{profile}.yaml"
    if not path.is_file():
        sys.exit(f"profile not found: {profile} ({path})")
    return load_yaml(path)


def profile_chain(profile: str, seen: tuple[str, ...] = ()) -> list[str]:
    """Ordered profile chain (root parent first .. this profile last), with
    `extends:` resolution and cycle detection."""
    if profile in seen:
        sys.exit(f"profile extends cycle: {' -> '.join([*seen, profile])}")
    parent = profile_data(profile).get("extends")
    chain = profile_chain(parent, (*seen, profile)) if parent else []
    return [*chain, profile]


def profile_modules(profile: str) -> list[str]:
    """String module ids across the extends chain (parent first), deduplicated.
    Non-string entries (e.g. `- enhancement: x`) are handled separately."""
    out: list[str] = []
    for name in profile_chain(profile):
        for module in profile_data(name).get("modules", []) or []:
            if isinstance(module, str) and module not in out:
                out.append(module)
    return out


def profile_enhancements(profile: str) -> list[str]:
    """Enhancement ids declared via `- enhancement: <id>` across the chain."""
    out: list[str] = []
    for name in profile_chain(profile):
        for module in profile_data(name).get("modules", []) or []:
            if isinstance(module, dict) and isinstance(module.get("enhancement"), str):
                eid = module["enhancement"]
                if eid not in out:
                    out.append(eid)
    return out


def load_enhancement_catalog() -> dict:
    """marketplace.yaml#enhancements as an {id: entry} map."""
    items = load_yaml(MARKETPLACE).get("enhancements", []) or []
    return {e["id"]: e for e in items if isinstance(e, dict) and "id" in e}


def handle_enhancements(profile: str) -> None:
    """Validate + report a profile's opt-in enhancements. Installs are DEFERRED
    user actions — this never runs an install command, so it is dry-run/CI safe.
    Exits non-zero on an unknown id or a conflicts_with collision."""
    enh = profile_enhancements(profile)
    if not enh:
        return
    catalog = load_enhancement_catalog()
    active = set(enh)
    for eid in enh:
        entry = catalog.get(eid)
        if entry is None:
            sys.exit(f"enhancement '{eid}': not in marketplace.yaml#enhancements")
        conflict = entry.get("conflicts_with")
        if conflict and conflict in active:
            sys.exit(f"enhancement conflict: '{eid}' conflicts_with '{conflict}'")
    for eid in enh:
        entry = catalog[eid]
        method = entry.get("install_method", "manual")
        cmd = entry.get("install", "(see doc)")
        print(f"# enhancement '{eid}' [{method}] — DEFERRED user action: {cmd}")
        if entry.get("smoke_test"):
            print(f"#   verify after manual install: {entry['smoke_test']}")


def expand_copy(src_rel: str, dest_rel: str) -> list[tuple[Path, Path]]:
    """Expand one manifest copy entry into (abs_source, abs_target) pairs.

    A trailing-slash source is a directory whose files map into dest by their
    path relative to the source; otherwise it is a single file.
    """
    src = REPO / src_rel
    if src_rel.endswith("/"):
        if not src.is_dir():
            return []
        pairs = []
        for f in sorted(src.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                pairs.append((f, HOME / dest_rel / f.relative_to(src)))
        return pairs
    if not src.is_file():
        return []
    return [(src, HOME / dest_rel)]


def resolve(modules: list[str]) -> tuple[list[tuple[Path, Path]], list[str]]:
    """Return (file pairs, notes) for a module list. Missing/non-copy modules note."""
    manifest = load_yaml(MANIFEST).get("modules", {})
    pairs: list[tuple[Path, Path]] = []
    notes: list[str] = []
    for module in modules:
        spec = manifest.get(module)
        if spec is None:
            notes.append(f"module '{module}': not in manifest (skipped)")
            continue
        kind = spec.get("kind", "copy")
        if kind != "copy":
            notes.append(
                f"module '{module}': kind={kind} (via {kind} step, not file-copy)"
            )
            continue
        before = len(pairs)
        for entry in spec.get("copies", []):
            pairs.extend(expand_copy(entry["src"], entry["dest"]))
        if len(pairs) == before:
            notes.append(f"module '{module}': no source files present yet (skipped)")
    return pairs, notes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_resolve(profile: str) -> None:
    handle_enhancements(profile)
    pairs, notes = resolve(profile_modules(profile))
    for src, dst in pairs:
        print(f"{src.relative_to(REPO)}  ->  {dst}")
    for note in notes:
        print(f"# {note}")
    print(f"# {len(pairs)} file(s) resolved for profile '{profile}'")


def cmd_apply(label: str, modules: list[str], dry_run: bool,
              no_backup: bool, force: bool) -> None:
    pairs, notes = resolve(modules)
    for note in notes:
        print(f"# {note}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = HOME / f".claude.backup-{stamp}"
    changed, created = 0, 0
    record_files = []

    for src, dst in pairs:
        exists = dst.exists()
        differs = not exists or sha256(src) != sha256(dst)
        if not differs:
            continue
        action = "update" if exists else "create"
        print(f"[{action}] {dst}")
        if dry_run:
            changed += exists
            created += not exists
            continue
        if exists and not no_backup:
            rel = dst.relative_to(HOME)
            (backup_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup_dir / rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        changed += exists
        created += not exists
        record_files.append({
            "target": str(dst),
            "source": str(src.relative_to(REPO)),
            "sha256": sha256(src),
        })

    print(f"# {created} create, {changed} update"
          + (" (dry-run; nothing written)" if dry_run else ""))
    if dry_run or not record_files:
        return
    write_record(label, record_files)
    print(f"# install record: {RECORD}")
    if not no_backup and backup_dir.exists():
        print(f"# backup: {backup_dir}")


def write_record(profile: str, files: list[dict]) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    head = run_git_head()
    RECORD.write_text(json.dumps({
        "rig_commit": head,
        "profile": profile,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }, indent=2))


def run_git_head() -> str:
    head = REPO / ".git" / "HEAD"
    try:
        ref = head.read_text().strip()
        if ref.startswith("ref:"):
            return (REPO / ".git" / ref.split(" ", 1)[1]).read_text().strip()
        return ref
    except OSError:
        return "unknown"


def cmd_rollback() -> None:
    if not RECORD.exists():
        print("no install record; nothing to roll back")
        return
    backups = sorted(HOME.glob(".claude.backup-*"))
    if not backups:
        print("no backup directory found; cannot roll back")
        sys.exit(1)
    latest = backups[-1]
    record = json.loads(RECORD.read_text())
    for entry in record.get("files", []):
        target = Path(entry["target"])
        saved = latest / target.relative_to(HOME)
        if saved.exists():
            shutil.copy2(saved, target)
            print(f"[restore] {target}")
    print(f"# rolled back from {latest}")


def cmd_uninstall() -> None:
    if not RECORD.exists():
        print("no install record; nothing to uninstall")
        return
    record = json.loads(RECORD.read_text())
    for entry in record.get("files", []):
        target = Path(entry["target"])
        if target.exists():
            target.unlink()
            print(f"[remove] {target}")
    RECORD.unlink()
    print("# removed install record")


def main() -> None:
    parser = argparse.ArgumentParser(description="bespoke installer engine")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_res = sub.add_parser("resolve")
    p_res.add_argument("profile")
    p_app = sub.add_parser("apply")
    p_app.add_argument("profile", nargs="?", help="profile name (or use --module)")
    p_app.add_argument("--module", help="install one module instead of a profile")
    p_app.add_argument("--dry-run", action="store_true")
    p_app.add_argument("--no-backup", action="store_true")
    p_app.add_argument("--force", action="store_true")
    sub.add_parser("rollback")
    sub.add_parser("uninstall")
    args = parser.parse_args()

    if args.cmd == "resolve":
        cmd_resolve(args.profile)
    elif args.cmd == "apply":
        if args.module:
            cmd_apply(args.module, [args.module], args.dry_run,
                      args.no_backup, args.force)
        elif args.profile:
            handle_enhancements(args.profile)
            cmd_apply(args.profile, profile_modules(args.profile),
                      args.dry_run, args.no_backup, args.force)
        else:
            parser.error("apply needs a profile name or --module <id>")
    elif args.cmd == "rollback":
        cmd_rollback()
    elif args.cmd == "uninstall":
        cmd_uninstall()


if __name__ == "__main__":
    main()
