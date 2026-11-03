UV := $(or $(shell command -v uv 2>/dev/null),.venv/bin/uv)

.PHONY: install fmt check test test-integration

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
