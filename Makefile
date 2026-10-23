ifeq ($(CONTAINERIZED),1)
RUFF ?= ruff
else
RUFF ?= uvx --from ruff==0.16.4 ruff
endif
# Quick dev commands never prepare a product/build image.
ifneq ($(filter lint format format-check check,$(MAKECMDGOALS)),)
override CONTAINERIZED := 1
endif
ifneq ($(CONTAINERIZED),1)
QUALITY_IMAGE := fastapitemplate:quality
RUNTIME_IMAGE := fastapitemplate:candidate
QUALITY_NETWORK := bridge
QUALITY_EXTRA_TARGETS := docs-check format-check chart-check
IMAGE_COMMAND = printf "%s\n" "notApplicable: maintenance source; runtime images belong to rendered applications"
VERIFY_COMMAND = $(QUALITY_RUN) python docker/release.py bundle-verify
BUILD_COMMAND = $(QUALITY_RUN) python docker/release.py bundle-build
OFFLINE_PREFLIGHT_COMMAND = true
CI_LOCAL_TARGETS := acceptance coverage build verify chart release-check
VERSION_COMMAND = $(QUALITY_RUN) python -m overlay.docker.chart_release version --chart-dir overlay/deploy/chart
RELEASE_CHECK_COMMAND = $(QUALITY_RUN) python -m overlay.docker.chart_release release-check --chart-dir overlay/deploy/chart
.PHONY: chart
chart: quality-image
	$(QUALITY_RUN) make chart
QUALITY_EXTRA_TARGETS += acceptance
CI_LOCAL_TARGETS ?= acceptance coverage build verify release-check
include docker/quality-python.mk
else
.DEFAULT_GOAL := help
UV ?= uv
HELM ?= helm

.PHONY: help install format lint typecheck test check compose

help: ## Show supported maintenance commands.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the locked maintenance environment.
	$(UV) sync --locked

format: ## Format owned Python tooling and regression tests.
	$(RUFF) check --fix tools tests
	$(RUFF) format tools tests

lint: ## Check formatting and lint.
	$(RUFF) check tools tests
	$(RUFF) format --check tools tests

typecheck: ## Check pinned composition tooling and its suite.
	$(UV) run --locked mypy

test: ## Run real Copier updates and the canonical composition suite.
	$(UV) run --locked pytest --junitxml=coverage/junit.xml --cov --cov-report=term-missing --cov-report=json --cov-report=xml

compose: ## Verify and assemble the pinned parent with the FastAPI overlay.
	$(UV) run --locked python tools/compose_template.py --repo . --smoke

chart: ## Package the shared deployment chart without publishing it.
	$(HELM) package overlay/deploy/chart --destination dist/charts
	$(UV) run --locked python -m overlay.docker.chart_release capture --chart-dir overlay/deploy/chart

chart-check: ## Validate the chart's accepted and rejected configurations.
	HELM=$(HELM) $(UV) run --locked pytest tests/chart_contract.py

format-check:
	$(RUFF) format --check tools tests
docs-check:
	$(UV) run --locked python tools/check_documentation.py --documents README.md AGENTS.md

check: lint format-check ## Fast lint-only gate; no tests/build.

acceptance: lint typecheck chart-check docs-check test ## Run every mandatory maintenance gate.
	$(UV) lock --check

endif

.PHONY: dev-policy-help
help: dev-policy-help
dev-policy-help:
	@printf '%s\n' 'Daily: make lint; explicit git push origin dev.' \
	  'Manual only: test, typecheck, coverage, build, acceptance, ci-local.' \
	  'Native lint tools must be installed; lint never syncs/builds the application.'
