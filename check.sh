#!/bin/bash
# Run all CI checks locally
# Usage: ./check.sh

set -e  # Exit on error

echo "🔍 Running CI checks locally..."
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "   Run: source .venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment: $VIRTUAL_ENV"
echo ""

# Format check
echo "📝 Checking code formatting..."
black --check pywiim tests || { echo "❌ Black formatting failed. Run: make format"; exit 1; }
isort --check-only pywiim tests || { echo "❌ isort formatting failed. Run: make format"; exit 1; }
echo "✅ Formatting OK"
echo ""

# Lint check
echo "🔎 Linting with Ruff..."
ruff check pywiim tests || { echo "❌ Ruff linting failed"; exit 1; }
echo "✅ Linting OK"
echo ""

# Type check
echo "🔬 Type checking with mypy..."
mypy pywiim || { echo "❌ Type checking failed"; exit 1; }
echo "✅ Type checking OK"
echo ""

# Tests
echo "🧪 Running tests..."
pytest tests/unit/ -v || { echo "❌ Tests failed"; exit 1; }
echo "✅ Tests passed"
echo ""

echo "🎉 All checks passed!"

