name: "Bug report"
description: Report a reproducible problem with the strategy, config, or signal engine.
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to file a bug. Please do **not** paste real API
        keys, secrets, or account details. Redact anything sensitive.
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: A clear and concise description of the bug.
      placeholder: Describe the actual behaviour.
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: What did you expect?
      description: What you expected to happen instead.
    validations:
      required: true
  - type: textarea
    id: reproduce
    attributes:
      label: Steps to reproduce
      description: Minimal steps, commands, or payloads to reproduce the issue.
      placeholder: |
        1. Run `python signal_engine/signal_engine.py --input ...`
        2. Observe ...
    validations:
      required: true
  - type: dropdown
    id: component
    attributes:
      label: Component
      options:
        - Strategy (CustomCryptoStrategy.py)
        - Configuration (config.example.json)
        - Signal engine (signal_engine.py)
        - Documentation
        - Other / not sure
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version / commit
      description: The release tag or commit SHA you are running.
    validations:
      required: false
  - type: input
    id: environment
    attributes:
      label: Environment
      description: OS, Python version, and (if relevant) Freqtrade version.
      placeholder: "Ubuntu 24.04, Python 3.12, Freqtrade 2024.9"
    validations:
      required: false
  - type: checkboxes
    id: checks
    attributes:
      label: Before submitting
      options:
        - label: I have redacted any API keys, secrets, or account details.
          required: true
        - label: I searched existing issues for a duplicate.
          required: true
