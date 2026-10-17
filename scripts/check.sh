#!/usr/bin/env bash
# Run the project's checks. There is no CI service on purpose: this script
# (also wired to `git push` through scripts/git-hooks/pre-push) is the gate.
#
#   scripts/check.sh          # everything, including the browser (E2E) tests
#   scripts/check.sh fast     # skip the E2E tests (about 2 seconds)
#
# Uses the local Python if it can import Django and pytest; otherwise runs
# inside the `sgchurch-test` Docker image, built automatically (the tag follows
# the requirements, so it rebuilds when they change).
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-${CHECK_MODE:-full}}"
PYTEST="python -m pytest tests -q -p no:cacheprovider --no-cov"
[ "$MODE" = "fast" ] && PYTEST="$PYTEST -m 'not e2e'"

STEPS="set -e
echo '==> Django system check'
python manage.py check
echo '==> Missing migrations?'
python manage.py makemigrations --check --dry-run
echo '==> Syntax errors and undefined names'
python -m flake8 . --select=E9,F63,F7,F82 --exclude=.git,venv,.venv,node_modules,staticfiles,migrations --count
echo '==> Tests ($MODE)'
$PYTEST"

export DJANGO_SETTINGS_MODULE=sg_church.settings.test

if python3 -c "import django, pytest" >/dev/null 2>&1; then
    echo "Running with the local Python environment"
    bash -c "$STEPS"
    exit
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "No Python environment with Django/pytest and Docker is not running." >&2
    echo "Start Docker (e.g. 'colima start') or install requirements-dev.txt." >&2
    exit 1
fi

TAG="sgchurch-test:$(cat requirements.txt requirements-dev.txt scripts/Dockerfile.test | shasum | cut -c1-12)"
if ! docker image inspect "$TAG" >/dev/null 2>&1; then
    echo "Building the test image $TAG (first run only, a few minutes)..."
    docker build -q -f scripts/Dockerfile.test -t "$TAG" .
fi
docker run --rm -v "$PWD":/app -w /app -e DJANGO_SETTINGS_MODULE "$TAG" bash -c "$STEPS"
