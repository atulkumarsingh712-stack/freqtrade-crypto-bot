# Contributing

Thanks for your interest in improving **freqtrade-crypto-bot**. This document
explains how to set up the project, run the checks, and submit changes.

## Ground rules

- Be respectful — see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Never commit secrets.** No API keys, tokens, or passwords, not even in
  tests or example files. CI and a pre-commit hook (`detect-private-key`) will
  flag them, but the responsibility is yours.
- Keep the trading logic deterministic and side-effect free where possible.
- Do not present this project as financial advice in code, comments, or docs.

## Development setup

```bash
git clone https://github.com/atulkumarsingh712-stack/freqtrade-crypto-bot.git
cd freqtrade-crypto-bot

python -m venv .venv && source .venv/bin/activate

# Development tooling (tests, lint, format, hooks)
pip install -r requirements-dev.txt
pre-commit install
```

The `signal_engine` package is pure standard library, so you can work on it
without installing Freqtrade. Installing the full runtime stack (Freqtrade +
TA-Lib) is only needed if you are changing the strategy or config:

```bash
make install   # installs requirements.txt
```

## Running the checks

```bash
make test      # pytest
make lint      # ruff
make format    # black + ruff --fix
make demo      # run the signal engine on the built-in example
```

All three of `test`, `lint`, and `format --check` must pass before a pull
request is merged. CI runs them on Python 3.10, 3.11, and 3.12.

## Submitting a change

1. Fork the repository and create a branch:
   `git checkout -b feat/short-description`.
2. Make your change. Add or update tests in `tests/`.
3. Ensure `make test` and `make lint` pass.
4. Commit with a clear message (see below).
5. Open a pull request and fill in the template.

## Commit messages

Use short, imperative subject lines, ideally following
[Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add ATR-scaled trailing stop
fix: correct ADX threshold comparison in signal engine
docs: clarify India tax notes in COMPLIANCE.md
test: cover HOLD branch of the decision tree
```

## Code style

- Line length 100, formatted with **black**.
- Linted with **ruff** (rules configured in `pyproject.toml`).
- Type hints on public functions; docstrings on modules and public callables.

## Reporting bugs and requesting features

Use the issue templates. For anything security-related, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
