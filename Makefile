.DEFAULT_GOAL := help
UV ?= uv
HELM ?= helm

.PHONY: help install format lint typecheck test check compose

help: ## Show supported maintenance commands.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the locked maintenance environment.
	$(UV) sync --locked

format: ## Format owned Python tooling and regression tests.
	$(UV) run --locked ruff check --fix tools tests
	$(UV) run --locked ruff format tools tests

lint: ## Check formatting and lint.
	$(UV) run --locked ruff check tools tests
	$(UV) run --locked ruff format --check tools tests

typecheck: ## Check pinned composition tooling and its suite.
	$(UV) run --locked mypy

test: ## Run real Copier updates and the canonical composition suite.
	$(UV) run --locked pytest --cov --cov-report=term-missing --cov-report=json --cov-report=xml

compose: ## Verify and assemble the pinned parent with the FastAPI overlay.
	$(UV) run --locked python tools/compose_template.py --repo . --smoke

chart: ## Package the shared deployment chart without publishing it.
	$(HELM) package overlay/deploy/chart --destination dist

chart-check: ## Validate the chart's accepted and rejected configurations.
	HELM=$(HELM) $(UV) run --locked pytest tests/chart_contract.py

check: lint typecheck test ## Run every mandatory maintenance gate.
	$(UV) lock --check
