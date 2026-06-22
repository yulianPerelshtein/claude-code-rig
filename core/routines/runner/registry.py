"""Load + validate ``core/routines/registry.yaml`` into ``Routine`` records.

The registry is the single source of truth binding a routine name to its body
(a skill slash-command or a deterministic script), its triggers, its target,
and its enforced outcome policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

VALID_OUTCOMES = {"report-only", "draft-pr", "local-write-allowlist"}
VALID_TRIGGERS = {"manual", "event", "scheduled"}
VALID_TARGETS = {"rig", "cwd"}
VALID_BODY_TYPES = {"skill", "script"}


class RegistryError(ValueError):
    """Raised when registry.yaml is malformed or violates the schema."""


@dataclass(frozen=True)
class Routine:
    name: str
    body: str
    description: str
    triggers: list[dict]
    target_default: str
    outcome: str
    enabled: bool = True
    # body_type "skill" -> invoke `/<body>` via `claude -p` (default).
    # body_type "script" -> the runner executes `script` directly (no LLM);
    # used by dream-loop, which reuses the shipped deterministic
    # core/hooks/session/dream_loop.py rather than a near-duplicate skill.
    body_type: str = "skill"
    script: str = ""
    # For script bodies that write their own report: a glob (expanded with
    # expanduser) the runner resolves to the newest file produced THIS run,
    # recorded as the run artifact. Lets the runner surface dream_loop.py's
    # report path without depending on the shipped hook printing it to stdout.
    artifact_hint: str = ""


def _validate(name: str, spec: dict) -> None:
    if not spec.get("body"):
        raise RegistryError(f"{name}: missing required 'body'")
    if spec.get("outcome") not in VALID_OUTCOMES:
        raise RegistryError(f"{name}: invalid outcome {spec.get('outcome')!r}")
    if spec.get("target_default") not in VALID_TARGETS:
        tgt = spec.get("target_default")
        raise RegistryError(f"{name}: invalid target_default {tgt!r}")
    body_type = spec.get("body_type", "skill")
    if body_type not in VALID_BODY_TYPES:
        raise RegistryError(f"{name}: invalid body_type {body_type!r}")
    if body_type == "script" and not spec.get("script"):
        raise RegistryError(f"{name}: body_type 'script' requires a 'script' path")
    for trigger in spec.get("triggers") or []:
        if trigger.get("type") not in VALID_TRIGGERS:
            raise RegistryError(f"{name}: invalid trigger {trigger!r}")


def load_registry(path: Path | str) -> dict[str, Routine]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if data.get("version") != 1:
        raise RegistryError("registry: unsupported or missing version (expected 1)")
    out: dict[str, Routine] = {}
    for name, spec in (data.get("routines") or {}).items():
        _validate(name, spec)
        out[name] = Routine(
            name=name,
            body=spec["body"],
            description=spec.get("description", ""),
            triggers=spec.get("triggers") or [],
            target_default=spec["target_default"],
            outcome=spec["outcome"],
            enabled=bool(spec.get("enabled", True)),
            body_type=spec.get("body_type", "skill"),
            script=spec.get("script", ""),
            artifact_hint=spec.get("artifact_hint", ""),
        )
    return out
