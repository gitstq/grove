#!/usr/bin/env bash
# One-key cross-platform build for Grove (Linux / macOS).
# Runs compile checks + unit tests, then builds a wheel and sdist into dist/.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

echo "==> [1/3] byte-compile"
"$PY" -m compileall -q src tests

echo "==> [2/3] unit tests"
"$PY" -m unittest discover -s tests

echo "==> [3/3] build wheel + sdist"
"$PY" -m pip install --quiet --upgrade build
"$PY" -m build

echo "==> Done. Artifacts:"
ls -1 dist/
