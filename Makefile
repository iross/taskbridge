.PHONY: install dev-install test test-all test-cov lint format typecheck pre-commit clean clean-all help

help:
	@echo "TaskBridge - Available Commands"
	@echo "================================"
	@echo "install       - Install package with dependencies"
	@echo "dev-install   - Install with dev dependencies + setup pre-commit"
	@echo "test          - Run unit tests"
	@echo "test-all      - Run all tests (unit + integration)"
	@echo "test-cov      - Run tests with coverage report"
	@echo "lint          - Check code with ruff"
	@echo "format        - Format code with ruff"
	@echo "typecheck     - Run type checking with ty"
	@echo "pre-commit    - Run all pre-commit hooks"
	@echo "clean         - Remove Python cache files"
	@echo "clean-all     - Remove cache files and virtual environment"

install:
	uv pip install -e .

dev-install:
	uv pip install -e ".[test,dev]"
	uv run pre-commit install

test:
	uv run pytest tests/unit -v

test-all:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=src/taskbridge --cov-report=html --cov-report=term

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run ty check src/

pre-commit:
	uv run pre-commit run --all-files

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov/

clean-all: clean
	rm -rf .venv/
