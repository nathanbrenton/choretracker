#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
    printf '[ERROR] Virtual environment not found: %s/.venv\n' "$PROJECT_DIR" >&2
    exit 1
fi

PYTHON="$PROJECT_DIR/.venv/bin/python"

printf '### ChoreTracker Validation\n\n'

printf '[INFO] Running tests\n'
"$PYTHON" -m pytest -v

printf '\n[INFO] Checking Ruff lint rules\n'
"$PYTHON" -m ruff check .

printf '\n[INFO] Checking Ruff formatting\n'
"$PYTHON" -m ruff format --check .

printf '\n[INFO] Checking Alembic model synchronization\n'
"$PYTHON" -m alembic check

printf '\n[INFO] Validating Docker Compose configuration\n'
docker compose config --quiet

printf '\n[PASS] All ChoreTracker validation checks passed\n'
