#!/usr/bin/env bash
# MIRRORNODE :: Bootstrap Script
# Seeds the local dev environment: vault dirs, deps, pyc cleanup
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
VAULT="$HOME/.mirrornode/oracle"

echo "[bootstrap] Creating Oracle Vault directories..."
mkdir -p "$VAULT"/{keys,logs,tmp}

echo "[bootstrap] Installing Poetry dependencies..."
cd "$BASE" && poetry install

echo "[bootstrap] Cleaning bytecode cache..."
find "$BASE" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$BASE" -name '*.pyc' -delete 2>/dev/null || true

echo "[bootstrap] Done. Run: poetry run uvicorn core.main:app --reload"
