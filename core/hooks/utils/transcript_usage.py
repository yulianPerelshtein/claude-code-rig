"""Token usage and API-equivalent cost of Claude Code sessions, read from transcripts.

The one place that reads `usage` out of `~/.claude/projects/<slug>/<sid>.jsonl`
(and its `subagents/` files) and prices it. The dollar figure is what the calls
would cost at API list price; a subscription bills nothing by it, so use it to
weigh sessions against each other, never as a bill.
"""

import json
from pathlib import Path

from utils.constants import TRANSCRIPT_DIR, safe_session_id

# USD per million tokens at API list price: input, output, cache read. Source: the
# claude-api skill's model table (cached 2026-10-06) and its prompt-caching page.
# Re-check when a new model id shows up in the transcripts (unpriced_calls > 0).
PRICES: dict[str, tuple[float, float, float]] = {
    "claude-fable-5-1": (10.0, 50.0, 0.25),
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-haiku-4-5": (1.0, 5.0, 0.10),
}
# Cache writes cost a multiple of the input price, by time to live.
WRITE_5M = 1.25
WRITE_1H = 2.0
# Haiku 5.5 charges 5x for prompts over 100k tokens.
LONG_PROMPT = {"claude-haiku-5-5": (100_000, 5.0)}
USAGE_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def _int(mapping: dict, field: str) -> int:
    value = mapping.get(field)
    return value if isinstance(value, int) else 0


def price_key(model: str) -> str | None:
    """The PRICES key a model id belongs to (dated ids match by prefix), or None."""
    for key in PRICES:
        if model == key or model.startswith(key + "-"):
            return key
    return None


def call_cost(model: str, usage: dict) -> float | None:
    """API-equivalent USD of one call, or None when the model is not in PRICES.

    Cache writes are split by TTL when `usage.cache_creation` says how; otherwise
    they are priced as 5-minute writes."""
    key = price_key(model)
    if key is None:
        return None
    inp, out, read = PRICES[key]
    write = _int(usage, "cache_creation_input_tokens")
    split = usage.get("cache_creation")
    if isinstance(split, dict):
        write_1h = _int(split, "ephemeral_1h_input_tokens")
        write_5m = write - write_1h
    else:
        write_1h, write_5m = 0, write
    read_tokens = _int(usage, "cache_read_input_tokens")
    prompt = _int(usage, "input_tokens") + write + read_tokens
    threshold, factor = LONG_PROMPT.get(key, (None, 1.0))
    scale = factor if threshold is not None and prompt > threshold else 1.0
    total = (
        _int(usage, "input_tokens") * inp
        + _int(usage, "output_tokens") * out
        + read_tokens * read
        + write_5m * inp * WRITE_5M
        + write_1h * inp * WRITE_1H
    )
    return total * scale / 1e6


def call_usages(path: Path) -> dict[str, tuple[str, dict]]:
    """requestId -> (model, usage) of each API call in one transcript file.

    Streaming writes one line per content block, all with the same requestId;
    the last carries the final output_tokens, so the max is kept."""
    calls: dict[str, tuple[str, dict]] = {}
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                usage = msg.get("usage") if isinstance(msg, dict) else None
                key = rec.get("requestId") or (msg or {}).get("id")
                if not isinstance(usage, dict) or not key:
                    continue
                kept = calls.get(key)
                if kept is None or _int(usage, "output_tokens") >= _int(
                    kept[1], "output_tokens"
                ):
                    calls[key] = (str((msg or {}).get("model") or ""), usage)
    except OSError:
        pass
    return calls


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def transcript_files(session_ids: set[str]) -> list[tuple[str, Path, bool]]:
    """(session_id, path, is_main) for each transcript file, oldest first."""
    files: list[tuple[float, str, Path, bool]] = []
    for sid in session_ids:
        if safe_session_id(sid) != sid:
            continue
        for path in TRANSCRIPT_DIR.glob(f"*/{sid}.jsonl"):
            files.append((_mtime(path), sid, path, True))
        for path in TRANSCRIPT_DIR.glob(f"*/{sid}/subagents/*.jsonl"):
            files.append((_mtime(path), sid, path, False))
    files.sort(key=lambda f: f[0])
    return [(sid, path, is_main) for _, sid, path, is_main in files]


def session_usage(session_ids: set[str], rebuild_tokens: int) -> dict[str, dict]:
    """session_id -> {"tokens", "api_usd", "rebuilds", "unpriced_calls"}.

    tokens and api_usd cover the main transcript and its subagents; rebuilds counts
    main-thread calls that wrote rebuild_tokens or more to the cache. A resumed
    session replays earlier calls into its new file, so each requestId is counted
    once, for the oldest file that holds it. Sessions without a transcript are
    absent."""
    seen: set[str] = set()
    out: dict[str, dict] = {}
    for sid, path, is_main in transcript_files(session_ids):
        slot = out.setdefault(
            sid, {"tokens": 0, "api_usd": 0.0, "rebuilds": 0, "unpriced_calls": 0}
        )
        for key, (model, usage) in call_usages(path).items():
            if key in seen:
                continue
            seen.add(key)
            tokens = sum(_int(usage, f) for f in USAGE_FIELDS)
            slot["tokens"] += tokens
            cost = call_cost(model, usage)
            if cost is not None:
                slot["api_usd"] += cost
            elif tokens:
                slot["unpriced_calls"] += 1
            if (
                is_main
                and _int(usage, "cache_creation_input_tokens") >= rebuild_tokens
            ):
                slot["rebuilds"] += 1
    return out
