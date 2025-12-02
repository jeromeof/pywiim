.PHONY: help format lint typecheck test clean install dev-install check

help:
	@echo "Available targets:"
	@echo "  make format      - Format code with Black and isort"
	@echo "  make lint        - Lint code with Ruff"
	@echo "  make typecheck   - Type check with mypy"
	@echo "  make test        - Run tests with pytest"
	@echo "  make check       - Run all CI checks (format check + lint + test)"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make install     - Install package"
	@echo "  make dev-install - Install package with dev dependencies"

format:
	@echo "Formatting code with Black and isort..."
	black pywiim tests
	isort pywiim tests

lint:
	@echo "Linting code with Ruff..."
	ruff check pywiim tests

typecheck:
	@echo "Type checking with mypy..."
	mypy pywiim

check:
	@echo "Running all CI checks..."
	@echo "1. Checking import sorting..."
	isort pywiim tests --check-only --diff || (echo "❌ Import sorting failed! Run 'make format' to fix." && exit 1)
	@echo "✅ Import sorting OK"
	@echo "2. Linting with Ruff..."
	ruff check pywiim tests || (echo "❌ Linting failed!" && exit 1)
	@echo "✅ Linting OK"
	@echo "3. Type checking with mypy..."
	mypy pywiim || (echo "❌ Type check failed!" && exit 1)
	@echo "✅ Type check OK"
	@echo "4. Running unit tests..."
	pytest tests/unit/ -x --tb=short -q
	@echo "✅ All checks passed!"

test:
	@echo "Running tests with pytest..."
	pytest

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=pywiim --cov-report=html --cov-report=term

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

