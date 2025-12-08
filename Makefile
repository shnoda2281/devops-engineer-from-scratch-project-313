.PHONY: install dev run lint format test setup

# То, что будет вызываться в hexlet-check через docker compose run app make setup
setup:
	uv sync

# Локальная установка зависимостей
install: setup

dev:
	uv run fastapi dev --host 0.0.0.0 --port 8080

run:
	uv run fastapi dev --host 0.0.0.0 --port 8080

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest
