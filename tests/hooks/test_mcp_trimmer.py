#!/usr/bin/env python3
"""Tests for core/hooks/post-tool/mcp_trimmer.py (PostToolUse MCP-output trimmer).

Locks the three contract points that previously made the hook a silent no-op:
  - reads the result from `tool_response` (not `tool_output`)
  - emits the rewrite under `updatedToolOutput` (not `updatedMCPToolOutput`)
  - only acts on mcp__* tools and only past the size threshold
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "core" / "hooks" / "post-tool" / "mcp_trimmer.py"

# Keep in sync with mcp_trimmer.MCP_TRIM_THRESHOLD.
THRESHOLD = 15_000


def run(payload: dict) -> str:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def mcp(content: str, tool_name: str = "mcp__plugin_x_serena__find_symbol") -> dict:
    return {"tool_name": tool_name, "tool_response": content}


def test_oversized_mcp_output_is_trimmed():
    out = run(mcp("x" * (THRESHOLD + 5_000)))
    assert out, "expected the hook to emit a rewrite for oversized output"
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PostToolUse"
    # The documented PostToolUse rewrite field — not updatedMCPToolOutput.
    assert "updatedToolOutput" in hso
    assert "OUTPUT TRIMMED" in hso["updatedToolOutput"]
    assert len(hso["updatedToolOutput"]) < THRESHOLD + 1_000


def test_small_mcp_output_passes_through():
    assert run(mcp("small result")) == ""


def test_non_mcp_tool_ignored_even_when_large():
    assert run({"tool_name": "Read", "tool_response": "y" * (THRESHOLD + 5_000)}) == ""


def test_reads_tool_response_not_tool_output():
    # The real PostToolUse payload carries the result under `tool_response`.
    # An oversized value under the old `tool_output` key must NOT trigger a trim.
    payload = {
        "tool_name": "mcp__plugin_x_serena__find_symbol",
        "tool_output": "z" * (THRESHOLD + 5_000),
    }
    assert run(payload) == ""


def test_structured_response_is_serialised_then_trimmed():
    big_list = ["item" * 1_000 for _ in range(10)]
    out = run(mcp(big_list))
    assert out
    payload = json.loads(out)
    assert "updatedToolOutput" in payload["hookSpecificOutput"]
