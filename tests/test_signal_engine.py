"""Tests for the deterministic market-regime signal engine."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signal_engine import (  # noqa: E402
    generate_signal,
    parse_snapshot,
)

# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #
BUY_PAYLOAD = {
    "timestamp": "2026-10-14T09:30:00Z",
    "symbol": "BTC/USDT",
    "price": 68123.45,
    "indicators": {
        "rsi": 58.2,
        "adx": 27.4,
        "ema20": 67900.0,
        "ema50": 67150.0,
        "ema200": 64200.0,
        "volume": 812345.6,
    },
}

SELL_PAYLOAD = {
    "timestamp": "2026-10-14T09:30:00Z",
    "symbol": "ETH/USDT",
    "price": 3000.0,
    "indicators": {
        "rsi": 78.0,
        "adx": 30.0,
        "ema20": 3100.0,
        "ema50": 3050.0,
        "ema200": 2900.0,
        "volume": 100.0,
    },
}

HOLD_PAYLOAD = {
    "timestamp": "2026-10-14T09:30:00Z",
    "symbol": "SOL/USDT",
    "price": 150.0,
    "indicators": {
        "rsi": 55.0,
        "adx": 15.0,
        "ema20": 151.0,
        "ema50": 150.5,
        "ema200": 140.0,
        "volume": 100.0,
    },
}

OUTPUT_KEYS = {
    "timestamp",
    "symbol",
    "signal",
    "confidence",
    "suggested_position_size_pct",
    "reasoning",
}


# --------------------------------------------------------------------------- #
#  Decision-tree branches
# --------------------------------------------------------------------------- #
def test_buy_when_all_conditions_met() -> None:
    result = generate_signal(BUY_PAYLOAD)
    assert result["signal"] == "BUY"
    assert result["confidence"] == "HIGH"


def test_sell_when_rsi_overbought() -> None:
    result = generate_signal(SELL_PAYLOAD)
    assert result["signal"] == "SELL_OR_CLOSE"
    assert result["confidence"] == "HIGH"


def test_sell_when_price_below_ema200() -> None:
    payload = json.loads(json.dumps(BUY_PAYLOAD))
    payload["price"] = 60000.0  # below ema200 (64200)
    result = generate_signal(payload)
    assert result["signal"] == "SELL_OR_CLOSE"


def test_sell_when_ema20_below_ema50() -> None:
    payload = json.loads(json.dumps(BUY_PAYLOAD))
    payload["indicators"]["ema20"] = 66000.0  # below ema50 (67150)
    result = generate_signal(payload)
    assert result["signal"] == "SELL_OR_CLOSE"


def test_hold_when_choppy() -> None:
    result = generate_signal(HOLD_PAYLOAD)
    assert result["signal"] == "HOLD"
    assert result["confidence"] == "NEUTRAL"


def test_buy_takes_precedence_over_later_rules() -> None:
    # A strong BUY setup that also happens to satisfy nothing in the sell rule.
    result = generate_signal(BUY_PAYLOAD)
    assert result["signal"] == "BUY"


# --------------------------------------------------------------------------- #
#  Output contract
# --------------------------------------------------------------------------- #
def test_output_has_exact_schema_keys() -> None:
    assert set(generate_signal(BUY_PAYLOAD).keys()) == OUTPUT_KEYS


@pytest.mark.parametrize("payload", [BUY_PAYLOAD, SELL_PAYLOAD, HOLD_PAYLOAD])
def test_position_size_within_bounds(payload: dict) -> None:
    size = generate_signal(payload)["suggested_position_size_pct"]
    assert 1 <= size <= 20


def test_buy_sizing_between_10_and_20() -> None:
    size = generate_signal(BUY_PAYLOAD)["suggested_position_size_pct"]
    assert 10 <= size <= 20


def test_non_buy_sizing_is_minimum() -> None:
    assert generate_signal(HOLD_PAYLOAD)["suggested_position_size_pct"] == 1
    assert generate_signal(SELL_PAYLOAD)["suggested_position_size_pct"] == 1


def test_determinism() -> None:
    assert generate_signal(BUY_PAYLOAD) == generate_signal(BUY_PAYLOAD)


# --------------------------------------------------------------------------- #
#  Validation
# --------------------------------------------------------------------------- #
def test_missing_price_raises() -> None:
    with pytest.raises(ValueError):
        generate_signal({"symbol": "BTC/USDT", "indicators": BUY_PAYLOAD["indicators"]})


def test_missing_indicator_raises() -> None:
    bad = {"symbol": "BTC/USDT", "price": 1.0, "indicators": {"rsi": 50.0}}
    with pytest.raises(ValueError):
        generate_signal(bad)


def test_non_numeric_price_raises() -> None:
    bad = {"symbol": "BTC/USDT", "price": "abc", "indicators": BUY_PAYLOAD["indicators"]}
    with pytest.raises(ValueError):
        generate_signal(bad)


def test_timestamp_defaults_when_absent() -> None:
    payload = {k: v for k, v in BUY_PAYLOAD.items() if k != "timestamp"}
    snap = parse_snapshot(payload)
    assert snap.timestamp.endswith("Z")


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def test_cli_demo_emits_valid_json() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "signal_engine" / "signal_engine.py"), "--demo"],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed = json.loads(proc.stdout)
    assert parsed["signal"] == "BUY"
    assert set(parsed.keys()) == OUTPUT_KEYS
