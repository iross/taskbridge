default:
    @just --list

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
