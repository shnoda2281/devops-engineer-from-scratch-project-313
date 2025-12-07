.PHONY: install setup dev run lint format test

setup:
	uv sync

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
