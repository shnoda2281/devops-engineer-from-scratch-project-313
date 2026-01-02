SHELL := /bin/sh

.PHONY: setup install lint test format run

setup:
	cd code && uv sync --system --frozen

install: setup

lint:
	cd code && uv run --system ruff check .

test:
	cd code && uv run --system pytest -q

format:
	cd code && uv run --system ruff format .

run:
	cd code && uv run --system fastapi run main:app --host 0.0.0.0 --port 8080
