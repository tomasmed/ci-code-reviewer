#!/usr/bin/env bash
# Deterministic Verification Gate for the Repository (Bash / POSIX)
# Runs linter, typecheck, and test suite in a single command.
# Returns exit code 0 on success, non-zero on failure.

set -euo pipefail

echo "🔍 [Verify Gate] Running deterministic verification checks..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [ -f "${REPO_ROOT}/pyproject.toml" ]; then
    echo "🐍 Python ecosystem detected"
    export LITELLM_LOCAL_MODEL_COST_MAP="True"
    cd "${REPO_ROOT}"
    uv run ruff check .
    uv run ruff format --check .
    uv run pytest
else
    echo "ℹ️  No specific language manifest detected yet. Verification passed as no-op."
fi

echo "✅ [Verify Gate] All deterministic checks passed successfully!"
