"""
CustomCryptoStrategy.py
=======================

A robust, production-ready Freqtrade strategy for trading volatile crypto
assets on a short intraday timeframe (5m or 15m).

Design summary
--------------
Trend classification   : EMA 20 / EMA 50 / EMA 200
Momentum / oscillator  : RSI (14)
Volatility / breakout  : Bollinger Bands (20, 2.0)
Regime filter          : ADX (14)

Entry (long)  -> macro uptrend + short-term momentum breakout inside a
                 confirmed trending regime, with RSI not yet overbought.
Exit          -> mean-reversion / momentum exhaustion, plus a dynamic
                 trailing stop-loss that locks in profit.

All indicator maths is vectorized with TA-Lib over a Pandas Series, so there
are no Python-level per-row loops in the hot path.

Usage
-----
    freqtrade trade --strategy CustomCryptoStrategy \
        --config user_data/config.json

The file is intentionally self-contained: only Freqtrade and TA-Lib are
required beyond the standard scientific stack.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter


class CustomCryptoStrategy(IStrategy):
    """
    EMA-trend + RSI-momentum + Bollinger/ADX regime strategy.

    Attributes
    ----------
    timeframe : str
        Candle interval. 5m or 15m are the supported intraday resolutions.
    can_short : bool
        Long-only strategy (short logic is intentionally not enabled).
    """

    # ------------------------------------------------------------------ #
    #  Framework configuration
    # ------------------------------------------------------------------ #
    INTERFACE_VERSION: int = 3

    # Intraday resolution; switch to "15m" for a slower, lower-noise variant.
    timeframe: str = "5m"

    # Long-only. Set to True and extend populate_entry/exit_trend to trade
    # both directions if a bear regime module is added later.
    can_short: bool = False

    # Number of candles required before the strategy produces signals.
    # Must exceed the longest indicator period (EMA 200) with headroom for
    # the initial NaN warm-up window.
    startup_candle_count: int = 220

    # ------------------------------------------------------------------ #
    #  Risk parameters (single source of truth for position management)
    # ------------------------------------------------------------------ #
    # Initial hard stop-loss: -4% from the entry price.
    stoploss: float = -0.04

    # Trailing stop-loss: once the trade is +3% in profit the stop begins
    # to trail, sitting 1.5% behind the best price seen.
    trailing_stop: bool = True
    trailing_stop_positive: float = 0.015  # offset (+1.5%)
    trailing_stop_positive_offset: float = 0.03  # activation threshold (+3%)
    trailing_only_offset_is_reached: bool = True  # do not trail before +3%

    # ------------------------------------------------------------------ #
    #  Strategy hyper-parameters (exposed for Freqtrade hyperopt)
    # ------------------------------------------------------------------ #
    # Regime filter: minimum ADX to consider the market "trending".
    buy_adx_threshold = IntParameter(18, 30, default=20, space="buy", optimize=True)

    # RSI entry band: momentum confirmation without buying into overbought.
    buy_rsi_min = IntParameter(35, 50, default=40, space="buy", optimize=True)
    buy_rsi_max = IntParameter(60, 70, default=65, space="buy", optimize=True)

    # RSI overbought exit level.
    sell_rsi_threshold = IntParameter(70, 85, default=75, space="sell", optimize=True)

    # Bollinger Band width (std-dev multiplier) for squeeze/breakout tuning.
    bollinger_std = DecimalParameter(1.5, 2.5, default=2.0, decimals=1, space="buy", optimize=True)

    # ------------------------------------------------------------------ #
    #  Indicator population
    # ------------------------------------------------------------------ #
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Compute every indicator used by the entry/exit rules.

        All calculations are vectorized TA-Lib calls on Pandas Series; no
        explicit ``for`` loops are used.

        Parameters
        ----------
        dataframe : DataFrame
            OHLCV candles supplied by Freqtrade (columns: open, high, low,
            close, volume, date).
        metadata : dict
            Pair metadata (contains at least ``"pair"``).

        Returns
        -------
        DataFrame
            The same dataframe enriched with indicator columns.
        """
        # --- Trend: exponential moving averages ------------------------- #
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # --- Momentum: RSI ---------------------------------------------- #
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # --- Volatility: Bollinger Bands --------------------------------- #
        bb_std = float(self.bollinger_std.value)
        bollinger = ta.BBANDS(
            dataframe,
            timeperiod=20,
            nbdevup=bb_std,
            nbdevdn=bb_std,
        )
        dataframe["bb_lower"] = bollinger["lowerband"]
        dataframe["bb_middle"] = bollinger["middleband"]
        dataframe["bb_upper"] = bollinger["upperband"]
        # Normalized band width: useful for squeeze detection / filtering.
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe[
            "bb_middle"
        ]

        # --- Regime: ATR + ADX ------------------------------------------ #
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        # Directional movement, handy for optional directional filtering.
        dataframe["plus_di"] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe, timeperiod=14)

        return dataframe

    # ------------------------------------------------------------------ #
    #  Entry logic
    # ------------------------------------------------------------------ #
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Mark long entries where the full trend + momentum + regime stack agrees.

        Conditions
        ----------
        1. Price above EMA 200        -> macro bullish trend.
        2. EMA 20 crosses above EMA 50 -> short-term momentum breakout.
        3. ADX above threshold         -> market is actively trending (no chop).
        4. RSI within [min, max]       -> momentum confirmed, not overbought.
        """
        dataframe.loc[
            (
                # 1. Macro bullish trend.
                (dataframe["close"] > dataframe["ema200"])
                # 2. Short-term momentum breakout (fresh cross only).
                & (dataframe["ema20"] > dataframe["ema50"])
                & (dataframe["ema20"].shift(1) <= dataframe["ema50"].shift(1))
                # 3. Trending regime, not sideways chop.
                & (dataframe["adx"] > self.buy_adx_threshold.value)
                # 4. RSI in the healthy-momentum band.
                & (dataframe["rsi"] > self.buy_rsi_min.value)
                & (dataframe["rsi"] < self.buy_rsi_max.value)
                # Guard against warm-up NaNs producing false signals.
                & (dataframe["ema200"].notna())
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "ema_cross_trend")

        return dataframe

    # ------------------------------------------------------------------ #
    #  Exit logic
    # ------------------------------------------------------------------ #
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Mark long exits on momentum exhaustion or trend reversal.

        The dynamic trailing stop-loss is handled natively by Freqtrade via
        the ``trailing_stop*`` class attributes, so it is not repeated here.

        Conditions
        ----------
        1. RSI crosses above the overbought threshold -> take profit.
        2. EMA 20 crosses below EMA 50                 -> trend reversal.
        """
        dataframe.loc[
            (
                # 1. Overbought take-profit.
                (dataframe["rsi"] > self.sell_rsi_threshold.value)
                & (dataframe["rsi"].shift(1) <= self.sell_rsi_threshold.value)
            )
            | (
                # 2. Short-term trend reversal.
                (dataframe["ema20"] < dataframe["ema50"])
                & (dataframe["ema20"].shift(1) >= dataframe["ema50"].shift(1))
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_or_ema_exit")

        return dataframe

    # ------------------------------------------------------------------ #
    #  Optional: custom stop-loss hook (left disabled)
    # ------------------------------------------------------------------ #
    def custom_stoploss(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float:
        """
        Return the native trailing-stop configuration.

        Freqtrade applies the class-level ``trailing_stop*`` attributes when
        this method is not overridden. We keep an explicit implementation so
        the risk model is auditable in one place and can be extended (e.g.
        ATR-scaled stops) without touching framework config.

        Returns
        -------
        float
            Stop-loss distance as a ratio (negative value relative to entry).
        """
        # Before the +3% activation threshold, hold the fixed -4% stop.
        if current_profit < self.trailing_stop_positive_offset:
            return self.stoploss
        # Once activated, the native trailing logic takes over; returning the
        # positive offset lets Freqtrade trail 1.5% behind the peak.
        return -self.trailing_stop_positive

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag,
        side: str,
        **kwargs,
    ) -> float:
        """
        Constrain leverage to 1x.

        This strategy is designed for spot / unleveraged exposure; override
        this method if a controlled leverage model is introduced.
        """
        return 1.0
