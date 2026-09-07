#!/bin/sh
# Pre-commit hooks for brandly-cli
# Install with: make pre-commit

set -e

echo "Installing pre-commit hooks for brandly-cli..."

# Use pip to install pre-commit if not present
if ! command -v pre-commit >/dev/null 2>&1; then
    python3 -m pip install pre-commit --quiet
fi

pre-commit install --install-hooks
echo "Pre-commit hooks installed."
echo ""
echo "Hooks configured:"
echo "  - ruff: lint on staged Python files"
echo "  - pytest-check: run tests before commit"
echo ""
echo "Test with: pre-commit run --all-files"
