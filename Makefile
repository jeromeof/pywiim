.PHONY: help format lint typecheck test clean install dev-install check release

help:
	@echo "Available targets:"
	@echo "  make format      - Format code with Black and isort"
	@echo "  make lint        - Lint code with Ruff"
	@echo "  make typecheck   - Type check with mypy"
	@echo "  make test        - Run tests with pytest"
	@echo "  make check       - Run all CI checks (format check + lint + test)"
	@echo "  make release     - Run checks, update version in pyproject.toml, commit, tag, and push"
	@echo "                    Usage: make release VERSION=2.1.53"
	@echo "                    ⚠️  Version in pyproject.toml will be auto-updated to match VERSION"
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
	@python -c "import xdist" 2>/dev/null && pytest tests/unit/ -x --tb=short -q -n auto || pytest tests/unit/ -x --tb=short -q
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

# Release workflow - ensures all checks pass before pushing
# 
# CRITICAL: This target automatically updates pyproject.toml version to match VERSION.
# The GitHub Actions workflow reads version from pyproject.toml, not the tag name.
# If versions don't match, PyPI publish will fail with "File already exists" error.
#
# Usage: make release VERSION=2.1.53
# 
# Steps:
# 1. Verifies/updates version in pyproject.toml to match VERSION
# 2. Runs all CI checks (lint, typecheck, tests)
# 3. Commits any uncommitted changes
# 4. Verifies version still matches (prevents PyPI failures)
# 5. Pushes commits
# 6. Creates and pushes tag
release:
ifndef VERSION
	$(error VERSION is required. Usage: make release VERSION=2.1.48)
endif
	@echo "🚀 Starting release v$(VERSION)..."
	@echo ""
	@echo "📋 Step 0: Verifying and updating version in pyproject.toml..."
	@CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	if [ "$$CURRENT_VERSION" != "$(VERSION)" ]; then \
		echo "⚠️  Version mismatch detected!"; \
		echo "   pyproject.toml has: $$CURRENT_VERSION"; \
		echo "   Release version: $(VERSION)"; \
		echo ""; \
		echo "📝 Updating pyproject.toml to version $(VERSION)..."; \
		sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml; \
		echo "✅ Version updated in pyproject.toml"; \
		echo "📝 Staging version update..."; \
		git add pyproject.toml; \
		echo "💾 Committing version bump..."; \
		git commit -m "chore: bump version to $(VERSION)" || true; \
		echo "✅ Version bump committed"; \
	else \
		echo "✅ Version in pyproject.toml matches release version ($(VERSION))"; \
	fi
	@echo ""
	@echo "📋 Step 1: Running all CI checks..."
	@$(MAKE) check
	@echo ""
	@echo "📋 Step 2: Committing any uncommitted changes..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "📝 Staging all changes..."; \
		git add -A; \
		echo "💾 Committing changes for release v$(VERSION)..."; \
		git commit -m "chore: prepare release v$(VERSION)" || true; \
		echo "✅ Changes committed"; \
	else \
		echo "✅ Working directory clean (no changes to commit)"; \
	fi
	@echo ""
	@echo "📋 Step 3: Verifying version still matches before tagging..."
	@CURRENT_VERSION=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	if [ "$$CURRENT_VERSION" != "$(VERSION)" ]; then \
		echo "❌ ERROR: Version mismatch after commits!"; \
		echo "   pyproject.toml has: $$CURRENT_VERSION"; \
		echo "   Release version: $(VERSION)"; \
		echo "   This will cause PyPI publish to fail!"; \
		exit 1; \
	fi
	@echo "✅ Version verified: pyproject.toml = $(VERSION)"
	@echo ""
	@echo "📋 Step 4: Pushing commits..."
	@git push origin main
	@echo ""
	@echo "📋 Step 5: Creating and pushing tag v$(VERSION)..."
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin main --tags
	@echo ""
	@echo "✅ Release v$(VERSION) complete!"
	@echo "   GitHub Actions will now build and publish to PyPI."

