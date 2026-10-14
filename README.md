# freqtrade-crypto-bot

[![CI](https://github.com/atulkumarsingh712-stack/freqtrade-crypto-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/atulkumarsingh712-stack/freqtrade-crypto-bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10 | 3.11 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linting-ruff-261230.svg)](https://github.com/astral-sh/ruff)

An algorithmic crypto-trading toolkit built around [Freqtrade](https://www.freqtrade.io/). Three pieces that work together:

- a **Freqtrade strategy** — EMA trend + RSI momentum + Bollinger/ADX regime filter,
- a **production-style configuration** — dynamic pairlist filtering and risk controls, and
- a **standalone signal engine** — turns a JSON market snapshot into a deterministic `BUY` / `SELL_OR_CLOSE` / `HOLD` verdict.

> **Disclaimer:** This is educational software, not financial advice. Trading crypto is high-risk and you can lose money. Run in `dry_run` mode first. You are responsible for your own capital and for your own legal and tax compliance. Read [DISCLAIMER.md](DISCLAIMER.md) and the jurisdiction-specific notes in [COMPLIANCE.md](COMPLIANCE.md) before use.

---

## Table of contents

- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [1. Freqtrade strategy](#1-freqtrade-strategy)
- [2. Configuration](#2-configuration)
- [3. Signal engine](#3-signal-engine)
- [Development](#development)
- [Project status & roadmap](#project-status--roadmap)
- [Legal & compliance](#legal--compliance)
- [License](#license)

---

## Repository layout

```
freqtrade-crypto-bot/
├── .github/
│   ├── workflows/ci.yml             # Lint, format, test, and secret scan
│   ├── ISSUE_TEMPLATE/              # Bug and feature request forms
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
├── config/
│   └── config.example.json          # Template config — copy to config.json
├── examples/
│   ├── payload_buy.json             # Sample signal-engine inputs
│   ├── payload_sell.json
│   └── payload_hold.json
├── signal_engine/
│   ├── __init__.py                  # Importable package API
│   └── signal_engine.py             # Deterministic regime classifier
├── tests/
│   └── test_signal_engine.py        # pytest suite
├── user_data/strategies/
│   └── CustomCryptoStrategy.py      # Freqtrade strategy (IStrategy v3)
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── COMPLIANCE.md                    # Jurisdiction notes (India, US, EU, UK, …)
├── CONTRIBUTING.md
├── DISCLAIMER.md                    # Risk, warranty and liability notice
├── LICENSE
├── Makefile
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── SECURITY.md
└── README.md
```

---

## Quick start

```bash
git clone https://github.com/atulkumarsingh712-stack/freqtrade-crypto-bot.git
cd freqtrade-crypto-bot

# Try the signal engine immediately — pure standard library, no deps needed
python signal_engine/signal_engine.py --demo
```

For the full bot you also need Freqtrade and the TA-Lib C library — see [Installation](#installation).

---

## 1. Freqtrade strategy

`user_data/strategies/CustomCryptoStrategy.py` — a long-only intraday strategy for volatile pairs on a 5m or 15m timeframe.

**Indicators:** EMA 20/50/200 (trend), RSI 14 (momentum), Bollinger Bands (20, 2σ) with a derived band-width for squeeze detection, ATR 14 and ADX 14 (regime). All computed with vectorized TA-Lib calls — no per-row loops.

**Long entry:** price above EMA 200, a fresh EMA 20 cross above EMA 50, ADX > 20, and RSI inside 40–65.

**Exit:** RSI crossing above 75 (take-profit) or EMA 20 crossing below EMA 50 (reversal), plus a native trailing stop.

**Risk parameters:**

| Parameter | Value |
|---|---|
| Hard stop-loss | −4% |
| Trailing activation | +3% profit |
| Trailing offset | +1.5% |
| Startup candles | 220 (covers the EMA 200 warm-up) |

The RSI band, ADX threshold, and Bollinger std-dev are exposed as `IntParameter` / `DecimalParameter` for `freqtrade hyperopt`.

## 2. Configuration

Copy the template and fill in your own values:

```bash
cp config/config.example.json config/config.json
```

Highlights:

- **Risk:** max 5 open trades, `stake_amount: "unlimited"` capped at 95% of tradable balance (`tradable_balance_ratio: 0.95`), −4% stop-loss, trailing stop activated at +3% with a +1.5% offset.
- **Pairlist:** `VolumePairList` (top 40 USDT pairs by 24h volume) → `AgeFilter` (min 30 days listed) → `SpreadFilter` (max 0.004) → `RangeStabilityFilter` / `VolatilityFilter` (drop illiquid and extreme-volatility assets) → `ShuffleFilter`.
- **Blacklist:** leveraged tokens (`BULL`/`BEAR`/`UP`/`DOWN`) and stablecoin pairs (USDC/BUSD/TUSD).
- **Execution:** 5m timeframe, `dry_run: true`, entry orders cancelled after 10 min unfilled, exits after 5 min.
- **Notifications:** Telegram and the REST API server blocks are enabled with placeholders.

### ⚠️ Secrets

`config.example.json` ships with **placeholder** credentials only. Never commit a real `config.json` — it is already listed in `.gitignore`, and a `detect-private-key` pre-commit hook plus a CI secret scan guard against accidents. The `jwt_secret_key` and `ws_token` must be freshly generated random strings, not the literals in the template. See [SECURITY.md](SECURITY.md).

## 3. Signal engine

`signal_engine/signal_engine.py` — a dependency-light, deterministic decision tree. Feed it a JSON snapshot; it returns strict JSON.

**Decision rules** (first match wins):

| # | Condition | Signal | Confidence |
|---|---|---|---|
| 1 | Price > EMA200 **and** EMA20 > EMA50 **and** ADX > 22 **and** RSI < 65 | `BUY` | HIGH |
| 2 | RSI > 75 **or** Price < EMA200 **or** EMA20 < EMA50 | `SELL_OR_CLOSE` | HIGH |
| 3 | otherwise | `HOLD` | NEUTRAL |

**Position sizing** is deterministic: `HOLD` and `SELL_OR_CLOSE` return `1`; `BUY` scales from 10 to 20 with momentum strength.

**Usage:**

```bash
python signal_engine/signal_engine.py --demo
python signal_engine/signal_engine.py --input examples/payload_buy.json
cat examples/payload_sell.json | python signal_engine/signal_engine.py
```

**As a library:**

```python
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
print(result["signal"])  # "BUY"
```

The engine does not fetch candles or compute indicators itself — it classifies whatever indicators you supply. Wire it to your own data feed.

---

## Installation

Freqtrade and TA-Lib are the main runtime dependencies. TA-Lib needs the native C library first:

```bash
# Debian/Ubuntu
sudo apt-get install build-essential libta-lib0-dev

# macOS
brew install ta-lib

pip install -r requirements.txt
```

### Running the bot

```bash
freqtrade download-data --config config/config.json --timeframe 5m
freqtrade trade --config config/config.json --strategy CustomCryptoStrategy
```

Start in `dry_run` mode (the template default) before risking real funds.

---

## Development

```bash
pip install -r requirements-dev.txt
pre-commit install

make test     # pytest
make lint     # ruff
make format   # black + ruff --fix
make demo     # run the signal engine on the built-in example
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow. CI runs lint, format
check, tests (with coverage), and a secret scan on Python 3.10–3.12.

## Project status & roadmap

**Status:** early (pre-1.0), under active development. The signal engine is
stable and tested; the strategy is a reference implementation to build on.

Planned:

- [ ] Backtest results and a reproducible `hyperopt` walkthrough
- [ ] An adapter that computes indicators from raw OHLCV so the signal engine can consume candles directly
- [ ] Optional short-side regime module
- [ ] Additional strategies (mean-reversion, breakout)

See [CHANGELOG.md](CHANGELOG.md) for released changes.

---

## Legal & compliance

This repository is software, not a financial service. It is not a broker, exchange, wallet, investment adviser, or crypto-asset service provider, and it provides no legal, tax, or investment advice. Crypto-asset trading is regulated differently in every country and can result in the total loss of your capital.

- [DISCLAIMER.md](DISCLAIMER.md) — risk, no-warranty, and liability notice.
- [COMPLIANCE.md](COMPLIANCE.md) — jurisdiction notes for India, the United States, the European Union, the United Kingdom, and other major markets, plus sanctions and export-control reminders.

You are solely responsible for complying with the laws, tax rules, and exchange terms of service that apply to you. Confirm your position with a qualified professional before deploying capital.

## License

MIT — see [LICENSE](LICENSE).

By cloning, forking, running, or deploying this software you accept the terms in [DISCLAIMER.md](DISCLAIMER.md) and [COMPLIANCE.md](COMPLIANCE.md).
