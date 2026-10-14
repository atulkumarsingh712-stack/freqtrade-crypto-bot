.PHONY: help install dev test lint format demo clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime dependencies (Freqtrade, TA-Lib)
	pip install -r requirements.txt

dev: ## Install development dependencies and git hooks
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Run the test suite
	pytest

lint: ## Check code style with ruff
	ruff check .

format: ## Auto-format with black and ruff
	black .
	ruff check --fix .

demo: ## Run the signal engine on the built-in example
	python signal_engine/signal_engine.py --demo

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
