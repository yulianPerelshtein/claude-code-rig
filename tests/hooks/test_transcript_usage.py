#!/usr/bin/env python3
"""Tests for core/hooks/utils/transcript_usage.py — API-equivalent pricing of calls.

Reading transcripts is covered through the session scorer (test_session_perf.py);
this file pins the pricing arithmetic, where a wrong rate silently skews every
session's cost.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "core" / "hooks"))

from utils.transcript_usage import call_cost  # noqa: E402


def test_call_cost_rates_by_model_and_cache_ttl():
    # Opus 5.5, 1M tokens written to the 1-hour cache: input $4 x 2.
    one_hour = {
        "cache_creation_input_tokens": 1_000_000,
        "cache_creation": {"ephemeral_1h_input_tokens": 1_000_000},
    }
    assert call_cost("claude-opus-5-5", one_hour) == pytest.approx(8.0)
    # No TTL split: priced as 5-minute writes, input $4 x 1.25.
    five_min = {"cache_creation_input_tokens": 1_000_000}
    assert call_cost("claude-opus-5-5", five_min) == pytest.approx(5.0)
    # Fable 5.1 reads its cache at $0.25, not 0.1x of its $10 input.
    reads = {"cache_read_input_tokens": 1_000_000}
    assert call_cost("claude-fable-5-1", reads) == pytest.approx(0.25)
    # A dated id prices as its model; Haiku 4.5 output is $5.
    out = {"output_tokens": 1_000_000}
    assert call_cost("claude-haiku-4-5-20251001", out) == pytest.approx(5.0)
    # Haiku 5.5 charges 5x once the prompt passes 100k tokens.
    long_prompt = {"input_tokens": 200_000}
    assert call_cost("claude-haiku-5-5", long_prompt) == pytest.approx(0.1)
    # An unknown model is unpriced, not free.
    assert call_cost("claude-new-9", out) is None
