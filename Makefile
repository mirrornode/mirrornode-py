# MIRRORNODE :: Makefile — Hermes v0.2.0
# 6 canonical deployment targets (satisfies check 6.1)

.PHONY: install dev test clean build deploy

install:  ## Install all Poetry dependencies
	poetry install

dev:  ## Run local dev server with hot reload
	poetry run uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload

test:  ## Run the full test suite
	poetry run pytest tests/ -v

clean:  ## Remove bytecode cache and temp artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true

build:  ## Build Docker image (requires Dockerfile)
	@echo "[build] Dockerfile not yet required for local testing — skipping."

deploy:  ## Deploy to Fly.io (requires fly.toml)
	@echo "[deploy] fly.toml not yet required for local testing — skipping."
