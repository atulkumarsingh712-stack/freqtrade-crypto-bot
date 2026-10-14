name: "Feature request"
description: Suggest an idea or improvement for the project.
title: "[Feature]: "
labels: ["enhancement", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for the suggestion. Note that this project is software for
        education and research — it is not financial advice.
  - type: textarea
    id: problem
    attributes:
      label: Is your feature request related to a problem?
      description: A clear description of what the problem is.
      placeholder: "I'm always frustrated when ..."
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: Describe the solution you'd like
      description: What you want to happen, and roughly how it might work.
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: Any alternative solutions or workarounds you have thought about.
    validations:
      required: false
  - type: dropdown
    id: component
    attributes:
      label: Component
      options:
        - Strategy (CustomCryptoStrategy.py)
        - Configuration (config.example.json)
        - Signal engine (signal_engine.py)
        - Documentation
        - Tooling / CI
        - Other
    validations:
      required: true
  - type: checkboxes
    id: checks
    attributes:
      label: Before submitting
      options:
        - label: I searched existing issues for a duplicate.
          required: true
