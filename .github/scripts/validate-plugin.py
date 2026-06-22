#!/usr/bin/env python3
"""Validate the plugin packaging: manifests parse, component paths exist,
and every SKILL.md carries name + description frontmatter.

Used by .github/workflows/plugin-validate.yml and runnable locally:
    python3 .github/scripts/validate-plugin.py
Exits 0 when valid, 1 with a list of problems otherwise.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PLUGIN = REPO / ".claude-plugin" / "plugin.json"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"


def resolve(rel: str) -> Path:
    """Resolve a ./-prefixed plugin component path to an absolute path.

    A prefix strip, not str.lstrip (which would eat the leading dot of a
    dotfile like ./.mcp.json).
    """
    return REPO / (rel[2:] if rel.startswith("./") else rel)


def load_json(path: Path, problems: list[str]) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        problems.append(f"missing: {path.relative_to(REPO)}")
    except json.JSONDecodeError as exc:
        problems.append(f"invalid JSON in {path.relative_to(REPO)}: {exc}")
    return None


def check_frontmatter(skill_md: Path, problems: list[str]) -> None:
    text = skill_md.read_text()
    if not text.startswith("---"):
        problems.append(f"{skill_md.relative_to(REPO)}: no frontmatter block")
        return
    block = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    for field in ("name:", "description:"):
        if field not in block:
            rel = skill_md.relative_to(REPO)
            problems.append(f"{rel}: frontmatter missing {field}")


def check_skill_dirs(paths: list[str], problems: list[str]) -> None:
    """Each skills component path is a parent scanned for <name>/SKILL.md."""
    for rel in paths:
        base = resolve(rel)
        if not base.is_dir():
            problems.append(f"skills path does not exist: {rel}")
            continue
        skills = sorted(base.glob("*/SKILL.md"))
        if not skills:
            problems.append(f"skills path has no <name>/SKILL.md: {rel}")
        for skill_md in skills:
            check_frontmatter(skill_md, problems)


def as_list(value: object) -> list[str]:
    """Component path fields are string | array; normalize to a list."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def check_paths_exist(plugin: dict, problems: list[str]) -> None:
    # agents + commands take FILE paths; CC rejects a directory here.
    for key in ("agents", "commands"):
        for rel in as_list(plugin.get(key)):
            target = resolve(rel)
            if not target.exists():
                problems.append(f"{key} path does not exist: {rel}")
            elif target.is_dir():
                problems.append(f"{key} must list files, not a directory: {rel}")
    for rel in as_list(plugin.get("outputStyles")):
        if not resolve(rel).exists():
            problems.append(f"outputStyles path does not exist: {rel}")
    for key in ("hooks", "mcpServers", "lspServers"):
        rel = plugin.get(key)
        if isinstance(rel, str) and not resolve(rel).exists():
            problems.append(f"{key} path does not exist: {rel}")


def main() -> None:
    problems: list[str] = []

    plugin = load_json(PLUGIN, problems)
    if plugin is not None:
        if not plugin.get("name"):
            problems.append("plugin.json: required field 'name' missing")
        check_skill_dirs(as_list(plugin.get("skills")), problems)
        check_paths_exist(plugin, problems)

    market = load_json(MARKETPLACE, problems)
    if market is not None:
        for field in ("name", "owner", "plugins"):
            if field not in market:
                problems.append(f"marketplace.json: required field '{field}' missing")
        if not market.get("description"):
            problems.append("marketplace.json: 'description' missing (strict)")

    for sidecar in (".mcp.json", ".lsp.json"):
        load_json(REPO / sidecar, problems)

    if problems:
        print("PLUGIN VALIDATION FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    print("plugin packaging valid: manifests parse, paths exist, frontmatter OK.")


if __name__ == "__main__":
    main()
