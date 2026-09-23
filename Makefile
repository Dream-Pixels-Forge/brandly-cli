# Brandly CLI — Makefile

PYTHON   := python3
PIP      := $(PYTHON) -m pip
PYTEST   := $(PYTHON) -m pytest
RUFF     := $(PYTHON) -m ruff
MYPY     := $(PYTHON) -m mypy
ROOT     ?= .

.PHONY: help install dev test cov lint lint-fix check-syntax type-check \
        build clean pre-commit ci e2e upgrade sync version-check

## Show this help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## Install package in editable mode + dev deps
install: ## install
	$(PIP) install -e ".[dev]"

## Install full dev environment (package + build tooling, mirrors CI)
dev: ## dev
	$(PIP) install -e ".[dev]" build twine

## Install pre-commit hooks
pre-commit: ## pre-commit
	$(PIP) install pre-commit
	pre-commit install

## Run full test suite
test: ## test
	$(PYTEST) tests/ -v --tb=short

## Run tests with coverage
cov: ## cov
	$(PYTEST) tests/ -v --tb=short --cov=src/brandly_cli --cov-report=term-missing --cov-report=html

## Run linter
lint: ## lint
	$(RUFF) check src/ tests/

## Fix lint issues automatically
lint-fix: ## lint-fix
	$(RUFF) check src/ tests/ --fix

## Type check
type-check: ## type-check
	$(MYPY) src/

## Syntax check all modules
check-syntax: ## check-syntax
	$(PYTHON) -m py_compile src/brandly_cli/*.py

## Build sdist + wheel (run 'make dev' first to install build/twine)
build: ## build
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

## Fail if pyproject.toml and __about__.py versions differ
version-check: ## version-check
	$(PYTHON) -c "import pathlib,re,sys; py=re.search(r'^version\\s*=\\s*\"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text(), re.M); ab=re.search(r'^__version__\\s*=\\s*\"([^\"]+)\"', pathlib.Path('src/brandly_cli/__about__.py').read_text(), re.M); sys.exit('version drift: pyproject=%s __about__=%s' % (py.group(1), ab.group(1)) if not py or not ab or py.group(1)!=ab.group(1) else 'version sync OK: %s' % py.group(1))"

## Run all quality gates (lint + type-check + test + build)
ci: version-check lint type-check test build ## ci
	@echo "All quality gates passed."

## End-to-end CLI smoke test
e2e: ## e2e
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ \
		init --name "Smoke" --idea "test" --style cinematic --shots 3
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ list
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ config
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ estimate --style cinematic --shots 5
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ director > /dev/null
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ models > /dev/null
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ memory view > /dev/null
	$(PYTHON) -m brandly_cli.cli --root /tmp/brandly-e2e-$$ prompt \
		--subject "wireless earbuds" --action "rotate" \
		--environment "desk" --shots 3 --style cinematic > /dev/null
	rm -rf /tmp/brandly-e2e-*
	@echo "E2E smoke test passed."

## Upgrade dev dependencies
upgrade: ## upgrade
	$(PIP) install --upgrade -e ".[dev]"

## Sync API keys into AI tool configs (requires env vars set)
sync: ## sync
	$(PYTHON) -m brandly_cli.cli sync

## Clean build/cache artifacts
clean: ## clean
	find src -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find tests -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build *.egg-info
	rm -rf /tmp/brandly-e2e-*
	@echo "Cleaned."
