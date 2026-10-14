# Disclaimer

**This software is provided for educational and research purposes only.**

## Not financial advice

Nothing in this repository constitutes financial, investment, legal, tax, or
accounting advice. The strategies, configurations, and signal logic here are
technical demonstrations, not recommendations to buy or sell any asset. No
author or contributor is your adviser. You are solely responsible for any
decision you make and any capital you deploy.

## Trading risk

Trading cryptocurrencies is highly volatile and carries a substantial risk of
loss, up to and including the **total loss of your capital**. Past performance —
including any backtest or hyperopt result — does not indicate future results.
Automated strategies can and do fail, sometimes quickly, in live markets.

- Always run in `dry_run` mode first.
- Never trade with money you cannot afford to lose.
- Test with small amounts before scaling up.

## No warranty

This software is distributed under the MIT License and comes with **no warranty
of any kind**, express or implied, including merchantability, fitness for a
particular purpose, title, and non-infringement. The authors and contributors
accept no liability for any loss, damage, or consequence — including trading
losses and lost profits — arising from the use of, or inability to use, this
software.

## Your legal and tax responsibility

You are responsible for complying with all laws that apply to you, including
tax, securities, commodities, anti-money-laundering, and sanctions rules, and
with the terms of service of any exchange or data provider you use. See
[COMPLIANCE.md](COMPLIANCE.md) for jurisdiction-specific notes, including India,
the United States, the European Union, and the United Kingdom.

## Security

Do **not** commit real API keys, secrets, or credentials. Only
`config/config.example.json` (with placeholders) belongs in version control.
Keep your real `config.json` local — it is listed in `.gitignore`. If you
suspect a key has been exposed, revoke it immediately at your exchange and
rotate any affected credentials.

## Jurisdiction

Cryptocurrency trading is restricted or regulated differently in every country.
It is your responsibility to ensure that your use of this software complies with
the laws and regulations that apply to you.

---

**By cloning, forking, running, or deploying this software you acknowledge that
you have read this notice, that you understand the risks, and that you accept
full responsibility for your use of it.**
