# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, use
GitHub's private reporting flow:

> Repository → **Security** tab → **Report a vulnerability**

This opens a private advisory visible only to the maintainers. Include:

- a description of the issue and its impact,
- steps to reproduce,
- affected files or components,
- any suggested fix, if you have one.

You can expect an acknowledgement within a few days. Please give us a reasonable
window to release a fix before disclosing publicly.

## Scope

This project is a set of local tools — a Freqtrade strategy, a configuration
template, and a signal engine. It runs on your own machine against your own
exchange account. There is no hosted service and no server-side component.

The most relevant risks are therefore **local and configuration-related**:

- **Leaked credentials.** Real API keys must never be committed. The repository
  ships only `config/config.example.json` with placeholders, and `.gitignore`
  excludes the real `config.json`. A `detect-private-key` pre-commit hook and CI
  guard against accidental commits.
- **Over-permissioned exchange keys.** When creating API keys for the bot,
  disable withdrawals and restrict to the minimum permissions required.
- **Unsafe dependency versions.** Dependabot is configured to raise updates.

## Hardening checklist for operators

- Run in `dry_run` mode before trading live.
- Use a dedicated, low-privilege API key with withdrawals disabled.
- Keep your real `config.json` local and out of version control.
- Rotate any key you suspect has been exposed, immediately, at the exchange.

## Supported versions

This project is pre-1.0 and under active development. Security fixes are applied
to the latest `main`.
