UV := $(or $(shell command -v uv 2>/dev/null),.venv/bin/uv)

.PHONY: install fmt check test test-integration coverage coverage-without-unit

install:
	$(UV) sync

fmt:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

test:
	$(UV) run pytest -q

test-integration:
	$(UV) run pytest -q -m integration

check:
	$(UV) run ruff format --check --no-cache .
	$(UV) run ruff check --no-cache .
	$(UV) run mypy --strict src tests/fakes
	$(UV) run pytest -q
	$(UV) run pytest -q -m integration

COVERAGE := --cov=stash --cov-branch --cov-report=

coverage:
	$(UV) run pytest -q $(COVERAGE)
	$(UV) run pytest -q -m integration $(COVERAGE) --cov-append --cov-report=term:skip-covered --cov-report=json:coverage.json

coverage-without-unit:
	$(UV) run pytest -q tests/acceptance tests/contract tests/integration $(COVERAGE)
	$(UV) run pytest -q -m integration tests/acceptance tests/contract tests/integration $(COVERAGE) --cov-append --cov-report=term:skip-covered --cov-report=json:coverage-without-unit.json
