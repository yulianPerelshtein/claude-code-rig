"""Registry loader: parse + validate routines/registry.yaml."""

import pytest
from runner.registry import RegistryError, Routine, load_registry


def _write(p, body):
    p.write_text(body)
    return p


def test_loads_known_routine(tmp_path):
    p = _write(
        tmp_path / "registry.yaml",
        "version: 1\n"
        "routines:\n"
        "  weekly-retro:\n"
        "    body: weekly-retro\n"
        "    description: d\n"
        "    triggers: [{type: manual}]\n"
        "    target_default: rig\n"
        "    outcome: draft-pr\n"
        "    enabled: true\n",
    )
    reg = load_registry(p)
    r = reg["weekly-retro"]
    assert isinstance(r, Routine)
    assert r.body == "weekly-retro"
    assert r.outcome == "draft-pr"
    assert r.enabled is True


def test_rejects_unknown_outcome(tmp_path):
    p = _write(
        tmp_path / "registry.yaml",
        "version: 1\nroutines:\n  x:\n    body: x\n    description: d\n"
        "    triggers: [{type: manual}]\n    target_default: cwd\n    outcome: YOLO\n",
    )
    with pytest.raises(RegistryError, match="outcome"):
        load_registry(p)


def test_rejects_unknown_version(tmp_path):
    p = _write(tmp_path / "registry.yaml", "version: 99\nroutines: {}\n")
    with pytest.raises(RegistryError, match="version"):
        load_registry(p)


def test_rejects_unknown_trigger_type(tmp_path):
    p = _write(
        tmp_path / "registry.yaml",
        "version: 1\nroutines:\n  x:\n    body: x\n    description: d\n"
        "    triggers: [{type: telepathy}]\n    target_default: cwd\n"
        "    outcome: report-only\n",
    )
    with pytest.raises(RegistryError, match="trigger"):
        load_registry(p)


def test_rejects_unknown_target(tmp_path):
    p = _write(
        tmp_path / "registry.yaml",
        "version: 1\nroutines:\n  x:\n    body: x\n    description: d\n"
        "    triggers: [{type: manual}]\n    target_default: moon\n"
        "    outcome: report-only\n",
    )
    with pytest.raises(RegistryError, match="target"):
        load_registry(p)


def test_shipped_registry_is_valid_and_complete():
    """The repo's own core/routines/registry.yaml parses and ships the v1 set."""
    from pathlib import Path

    repo_reg = Path(__file__).resolve().parents[2] / "core/routines/registry.yaml"
    reg = load_registry(repo_reg)
    assert set(reg) == {
        "begin-work",
        "wrap-up",
        "weekly-retro",
        "monthly-drift",
        "dream-loop",
    }
    # dream-loop runs the shipped script directly (no /dream-loop skill).
    assert reg["dream-loop"].body_type == "script"
    assert reg["dream-loop"].script.endswith("dream_loop.py")
    # the other four are skill-bodied
    assert reg["weekly-retro"].body_type == "skill"
