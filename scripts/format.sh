#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
    printf '[ERROR] Virtual environment not found: %s/.venv\n' "$PROJECT_DIR" >&2
    exit 1
fi

PYTHON="$PROJECT_DIR/.venv/bin/python"

printf '### ChoreTracker Python Formatting\n\n'

# Format first so generated files, including Alembic migrations, are wrapped
# before the linter evaluates line-length and import rules.
printf '[INFO] Applying Ruff formatting\n'
"$PYTHON" -m ruff format .

printf '\n[INFO] Applying safe Ruff lint fixes\n'
"$PYTHON" -m ruff check . --fix

# Lint fixes can alter imports or code layout, so format once more afterward.
printf '\n[INFO] Applying final Ruff formatting pass\n'
"$PYTHON" -m ruff format .

printf '\n[INFO] Verifying lint and formatting\n'
"$PYTHON" -m ruff check .
"$PYTHON" -m ruff format --check .

printf '\n[PASS] Python formatting and lint fixes completed\n'
