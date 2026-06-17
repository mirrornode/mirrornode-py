# MIRRORNODE :: Makefile — Hermes v0.2.0
# Canonical deployment targets expected by thoth_preflight check 6.1

.PHONY: preflight keys env first-boot docker-build fly-deploy install dev test clean

preflight:  ## Run THOTH pre-flight verification
	poetry run python3 thoth_preflight.py

keys:  ## Generate Ed25519 keypair into Oracle Vault
	poetry run python3 scripts/generate_keys.py

env:  ## Copy .env.example to .env (edit before use)
	@[ -f .env ] && echo ".env already exists, skipping." || cp .env.example .env && echo ".env created from template."

first-boot:  ## Full first-run sequence: env + keys + install + preflight
	$(MAKE) env
	$(MAKE) install
	$(MAKE) keys
	$(MAKE) preflight

docker-build:  ## Build Docker image
	@echo "[docker-build] Dockerfile not yet required for local testing — skipping."

fly-deploy:  ## Deploy to Fly.io
	@echo "[fly-deploy] fly.toml not yet required for local testing — skipping."

install:  ## Install all Poetry dependencies
	poetry install

dev:  ## Run local dev server with hot reload
	poetry run uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload

test:  ## Run the full test suite
	poetry run pytest tests/ -v

clean:  ## Remove bytecode cache and temp artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
