.DEFAULT_GOAL := help

.PHONY: help sync run test test-file format lint clean db-upgrade docker-build agent-summary agent-check

help:
	@echo "Targets:"
	@echo "  make sync       - install dependencies (including dev tools)"
	@echo "  make run        - run the Telegram bot"
	@echo "  make test       - run all tests"
	@echo "  make test-file FILE=tests/test_shop.py - run one test file"
	@echo "  make lint       - run Ruff checks"
	@echo "  make format     - format Python files with Ruff"
	@echo "  make db-upgrade - apply Alembic migrations"
	@echo "  make docker-build - build the production image"
	@echo "  make agent-summary - print a compact JSON repository map"
	@echo "  make agent-check - validate architecture boundaries"
	@echo "  make clean      - remove caches"

sync:
	uv sync --extra dev

run:
	uv run yuqa

test:
	uv run pytest -q

test-file:
	@test -n "$(FILE)" || (echo "Usage: make test-file FILE=tests/test_shop.py" && exit 1)
	uv run pytest -q "$(FILE)"

lint:
	uv run ruff check yuqa tests main.py

format:
	uv run ruff format yuqa tests main.py

build:
	uv run nuitka main.py

# run binary file only on linux
brun:
	bash main.sh

db-upgrade:
	uv run alembic upgrade head

agent-summary:
	uv run python scripts/agent_audit.py summary

agent-check:
	uv run python scripts/agent_audit.py check

clean:
	find yuqa tests -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache
