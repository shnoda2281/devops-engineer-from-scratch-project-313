SHELL := /bin/sh

.PHONY: setup install lint test format run

setup:
	cd code && UV_PYTHON_DOWNLOADS=never UV_SYSTEM_PYTHON=1 uv sync --system --frozen

install: setup

lint:
	uv run --system ruff check .

test:
	uv run --system pytest -q

format:
	uv run --system ruff format .

run:
	uv run --system fastapi run main:app --host 0.0.0.0 --port 8080
