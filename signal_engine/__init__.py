"""Deterministic market-regime signal engine.

Public API::

    from signal_engine import generate_signal

    result = generate_signal({
        "symbol": "BTC/USDT",
        "price": 68123.45,
        "indicators": {
            "rsi": 58.2, "adx": 27.4,
            "ema20": 67900.0, "ema50": 67150.0, "ema200": 64200.0,
            "volume": 812345.6,
        },
    })
"""

from .signal_engine import (
    ADX_TREND_FLOOR,
    POSITION_MAX,
    POSITION_MIN,
    RSI_BUY_CEILING,
    RSI_OVERBOUGHT,
    Indicators,
    MarketSnapshot,
    Signal,
    classify,
    generate_signal,
    parse_snapshot,
    to_output_dict,
)

__all__ = [
    "ADX_TREND_FLOOR",
    "POSITION_MAX",
    "POSITION_MIN",
    "RSI_BUY_CEILING",
    "RSI_OVERBOUGHT",
    "Indicators",
    "MarketSnapshot",
    "Signal",
    "classify",
    "generate_signal",
    "parse_snapshot",
    "to_output_dict",
]

__version__ = "0.1.0"
