# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-14

### Added

- **Freqtrade strategy** (`user_data/strategies/CustomCryptoStrategy.py`):
  long-only intraday strategy using EMA 20/50/200, RSI 14, Bollinger Bands
  (20, 2σ), ATR 14, and ADX 14, with a native trailing stop-loss.
- **Configuration template** (`config/config.example.json`): 5 open trades max,
  95% tradable-balance cap, −4% stop-loss, trailing stop at +3%/+1.5%, dynamic
  `VolumePairList` (top 40 USDT pairs) with `AgeFilter`, `SpreadFilter`,
  `RangeStabilityFilter`, `VolatilityFilter`, and `ShuffleFilter`, plus a
  leveraged-token and stablecoin blacklist.
- **Signal engine** (`signal_engine/signal_engine.py`): a deterministic
  market-regime classifier producing `BUY` / `SELL_OR_CLOSE` / `HOLD` verdicts
  as strict JSON, with a CLI and an importable API.
- **Legal notices**: `DISCLAIMER.md` and `COMPLIANCE.md` (India, US, EU, UK,
  and other major markets).
- **Tests** (`tests/`), **example payloads** (`examples/`), CI workflow,
  issue/PR templates, and Dependabot configuration.
- **Project tooling**: `pyproject.toml`, `Makefile`, pre-commit hooks,
  `.editorconfig`, `.gitattributes`.
- **Community health files**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`.
