#!/bin/bash
# Sanity Check for Career Dreamer Project
# Verifies environment isolation and guideline compliance.

echo "🔍 Starting Sanity Check..."

# 1. Check for uv installation and project lock
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' not found. Please install uv (https://github.com/astral-sh/uv)."
    exit 1
fi

if [ ! -f "uv.lock" ]; then
    echo "❌ Error: 'uv.lock' not found. Run 'uv lock' to generate it."
    exit 1
fi

# 2. Check for local environment isolation
echo "✅ Environment: 'uv' project detected."

# 3. Audit for global dependency leaks (simple check for requirements.txt vs pyproject.toml)
if [ -f "requirements.txt" ]; then
    echo "⚠️  Warning: 'requirements.txt' still exists. It should be removed to ensure 'uv' is the source of truth."
fi

# 4. Run Lint Audit
echo "🧹 Running Lint Audit (Ruff)..."
uv run ruff check .
if [ $? -eq 0 ]; then
    echo "✅ Lint: All checks passed."
else
    echo "❌ Lint: Failed. Run 'uv run ruff check --fix .' to resolve."
    exit 1
fi

# 5. Run Test Audit
echo "🧪 Running Test Audit (Pytest)..."
uv run pytest
if [ $? -eq 0 ]; then
    echo "✅ Tests: All checks passed."
else
    echo "❌ Tests: Some tests failed."
    exit 1
fi

echo "🚀 All systems go! The project adheres to engineering guidelines."
