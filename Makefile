.DEFAULT_GOAL := help
UV_CACHE_DIR ?= $(CURDIR)/.cache/uv
UV := env UV_CACHE_DIR=$(UV_CACHE_DIR) uv

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
	$(UV) sync --extra dev --extra docker

run:
	$(UV) run main.py
	make clean

test:
	$(UV) run pytest -q
	make clean

test-file:
	@test -n "$(FILE)" || (echo "Usage: make test-file FILE=tests/test_shop.py" && exit 1)
	$(UV) run pytest -q "$(FILE)"
	make clean

docker-build:
	docker build -t yuqa:latest ./

docker-run: docker-build
	docker run -d yuqa:latest

lint:
	$(UV) run ruff check src tests main.py

format:
	$(UV) run ruff format src tests main.py


db-upgrade:
	$(UV) run alembic upgrade head

agent-summary:
	$(UV) run python scripts/agent_audit.py summary

agent-check:
	$(UV) run python scripts/agent_audit.py check

clean:
	find src tests -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .cache/uv
