#!/usr/bin/env python3
"""
signal_engine.py
================

Automated Market Regime Classifier and Algorithmic Trading Signal Engine.

This module implements a *deterministic* decision tree over real-time crypto
market data. It consumes a JSON payload containing the current price, 15m
OHLCV candles, and pre-computed indicators (RSI, ADX, EMA 20/50/200, Volume),
and emits a strictly-formatted JSON trading signal.

Input schema (what you feed in)
-------------------------------
{
  "timestamp": "2026-10-14T09:30:00Z",   # optional; defaults to now (UTC)
  "symbol": "BTC/USDT",
  "price": 68123.45,                      # current price (required)
  "indicators": {
    "rsi": 58.2,                          # RSI (14)
    "adx": 27.4,                          # ADX (14)
    "ema20": 67900.0,
    "ema50": 67150.0,
    "ema200": 64200.0,
    "volume": 812345.6                    # 15m candle volume
  },
  "candles_15m": [                        # optional, for audit / future use
    {"time": 1728894600, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}
  ]
}

Output schema (what it emits)
-----------------------------
{
  "timestamp": "<UTC Timestamp>",
  "symbol": "<Symbol>",
  "signal": "BUY | SELL_OR_CLOSE | HOLD",
  "confidence": "HIGH | MEDIUM | LOW",
  "suggested_position_size_pct": <number between 1 and 20>,
  "reasoning": "<1-sentence concise explanation>"
}

Decision rules (evaluated in order; first match wins)
----------------------------------------------------
1. BUY            : Price > EMA200 AND EMA20 > EMA50 AND ADX > 22 AND RSI < 65
2. SELL_OR_CLOSE  : RSI > 75 OR Price < EMA200 OR EMA20 < EMA50
3. HOLD           : otherwise

Position sizing
---------------
The spec only bounds the output to [1, 20] but does not define the mapping, so
a deterministic rule is used here and can be swapped via ``SizingPolicy``:

  * HOLD            -> 1   (no conviction / stand aside)
  * SELL_OR_CLOSE   -> 1   (de-risking, no new exposure)
  * BUY             -> scaled 10..20 by momentum strength (ADX above the 22
                       floor and RSI headroom below 65); a bare-minimum BUY
                       that only just clears the gates sizes at 10.

Determinism: identical inputs always produce identical outputs. No RNG, no
wall-clock dependence except the defaulted timestamp.

Usage
-----
    python signal_engine.py --input payload.json
    cat payload.json | python signal_engine.py
    python signal_engine.py --demo          # runs the built-in example
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# --------------------------------------------------------------------------- #
#  Thresholds (single source of truth; mirror the decision-tree spec)
# --------------------------------------------------------------------------- #
ADX_TREND_FLOOR: float = 22.0  # ADX must exceed this to confirm a trend
RSI_BUY_CEILING: float = 65.0  # RSI must stay below this to allow entry
RSI_OVERBOUGHT: float = 75.0  # RSI above this forces SELL_OR_CLOSE

# Position-sizing envelope required by the output schema.
POSITION_MIN: int = 1
POSITION_MAX: int = 20


@dataclass(frozen=True)
class Indicators:
    """Computed technical indicators for a single symbol snapshot."""

    rsi: float
    adx: float
    ema20: float
    ema50: float
    ema200: float
    volume: float


@dataclass(frozen=True)
class MarketSnapshot:
    """A single point-in-time view of the market for one symbol."""

    symbol: str
    price: float
    indicators: Indicators
    timestamp: str
    candles_15m: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class Signal:
    """The engine's output verdict."""

    signal: str
    confidence: str
    suggested_position_size_pct: int
    reasoning: str


# --------------------------------------------------------------------------- #
#  Parsing
# --------------------------------------------------------------------------- #
def parse_snapshot(payload: dict[str, Any]) -> MarketSnapshot:
    """
    Validate and normalise a raw JSON payload into a ``MarketSnapshot``.

    Raises
    ------
    ValueError
        If required fields are missing or non-numeric.
    """
    try:
        symbol = str(payload["symbol"])
        price = float(payload["price"])
    except KeyError as exc:
        raise ValueError(f"Missing required top-level field: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Field 'price' must be numeric: {exc}") from exc

    raw_ind = payload.get("indicators")
    if not isinstance(raw_ind, dict):
        raise ValueError("Missing required object: 'indicators'")

    try:
        indicators = Indicators(
            rsi=float(raw_ind["rsi"]),
            adx=float(raw_ind["adx"]),
            ema20=float(raw_ind["ema20"]),
            ema50=float(raw_ind["ema50"]),
            ema200=float(raw_ind["ema200"]),
            volume=float(raw_ind.get("volume", 0.0)),
        )
    except KeyError as exc:
        raise ValueError(f"Missing required indicator: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Indicator values must be numeric: {exc}") from exc

    timestamp = str(
        payload.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    return MarketSnapshot(
        symbol=symbol,
        price=price,
        indicators=indicators,
        timestamp=timestamp,
        candles_15m=payload.get("candles_15m"),
    )


# --------------------------------------------------------------------------- #
#  Decision tree
# --------------------------------------------------------------------------- #
def _is_buy(snap: MarketSnapshot) -> bool:
    """Strong bullish trend continuation with momentum confirmation."""
    i = snap.indicators
    return (
        snap.price > i.ema200
        and i.ema20 > i.ema50
        and i.adx > ADX_TREND_FLOOR
        and i.rsi < RSI_BUY_CEILING
    )


def _is_sell_or_close(snap: MarketSnapshot) -> bool:
    """Overbought exhaustion or a structural trend break."""
    i = snap.indicators
    return i.rsi > RSI_OVERBOUGHT or snap.price < i.ema200 or i.ema20 < i.ema50


def _size_buy(snap: MarketSnapshot) -> int:
    """
    Deterministically size a BUY between 10 and 20 (the schema's [1, 20] range).

    Strength is the average of two normalised components:
      * ADX headroom above the 22 floor, saturating at ADX 40.
      * RSI headroom below the 65 ceiling, saturating near RSI 45.

    A BUY that only just clears the gates sizes at 10; a maximally strong
    reading sizes at 20.
    """
    i = snap.indicators
    adx_component = min(max((i.adx - ADX_TREND_FLOOR) / (40.0 - ADX_TREND_FLOOR), 0.0), 1.0)
    rsi_component = min(max((RSI_BUY_CEILING - i.rsi) / (RSI_BUY_CEILING - 45.0), 0.0), 1.0)
    strength = (adx_component + rsi_component) / 2.0
    return int(round(10 + strength * 10))


def classify(snap: MarketSnapshot) -> Signal:
    """
    Execute the deterministic decision tree and return a ``Signal``.

    Rules are evaluated in order and the first match wins, so a fully bullish
    setup reports BUY even if a later rule could also fire.
    """
    i = snap.indicators

    # Rule 1: BUY.
    if _is_buy(snap):
        return Signal(
            signal="BUY",
            confidence="HIGH",
            suggested_position_size_pct=_size_buy(snap),
            reasoning=(
                "Strong bullish trend continuation with momentum confirmation "
                f"(price > EMA200, EMA20 > EMA50, ADX {i.adx:.1f} > {ADX_TREND_FLOOR:g}, "
                f"RSI {i.rsi:.1f} < {RSI_BUY_CEILING:g})."
            ),
        )

    # Rule 2: SELL_OR_CLOSE.
    if _is_sell_or_close(snap):
        triggers = []
        if i.rsi > RSI_OVERBOUGHT:
            triggers.append(f"RSI {i.rsi:.1f} > {RSI_OVERBOUGHT:g} (overbought)")
        if snap.price < i.ema200:
            triggers.append("price below EMA200 (macro trend broken)")
        if i.ema20 < i.ema50:
            triggers.append("EMA20 below EMA50 (short-term trend broken)")
        return Signal(
            signal="SELL_OR_CLOSE",
            confidence="HIGH",
            suggested_position_size_pct=POSITION_MIN,
            reasoning="Exit or de-risk: " + "; ".join(triggers) + ".",
        )

    # Rule 3: HOLD.
    return Signal(
        signal="HOLD",
        confidence="NEUTRAL",
        suggested_position_size_pct=POSITION_MIN,
        reasoning="Market is choppy or lacking a clear directional trend.",
    )


# --------------------------------------------------------------------------- #
#  Output
# --------------------------------------------------------------------------- #
def to_output_dict(snap: MarketSnapshot, sig: Signal) -> dict[str, Any]:
    """Assemble the exact output schema, with the position size clamped."""
    size = max(POSITION_MIN, min(POSITION_MAX, int(sig.suggested_position_size_pct)))
    return {
        "timestamp": snap.timestamp,
        "symbol": snap.symbol,
        "signal": sig.signal,
        "confidence": sig.confidence,
        "suggested_position_size_pct": size,
        "reasoning": sig.reasoning,
    }


def generate_signal(payload: dict[str, Any]) -> dict[str, Any]:
    """End-to-end: raw JSON payload in, output-schema dict out."""
    snap = parse_snapshot(payload)
    return to_output_dict(snap, classify(snap))


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
_DEMO_PAYLOAD: dict[str, Any] = {
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


def _read_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.demo:
        return _DEMO_PAYLOAD
    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            return json.load(fh)
    return json.load(sys.stdin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic crypto market-regime signal engine."
    )
    parser.add_argument("--input", help="Path to a JSON payload file.")
    parser.add_argument("--demo", action="store_true", help="Run the built-in example payload.")
    args = parser.parse_args(argv)

    try:
        payload = _read_payload(args)
        result = generate_signal(payload)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Strict JSON, no markdown preamble or prose.
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
