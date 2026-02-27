SHELL := /bin/bash

.PHONY: setup install lint test format run

# КЛЮЧЕВОЕ: без --system, только через ENV
setup:
	UV_SYSTEM_PYTHON=1 UV_PYTHON_DOWNLOADS=never uv sync --frozen

install: setup

lint:
	UV_SYSTEM_PYTHON=1 uv run ruff check .

test:
	UV_SYSTEM_PYTHON=1 uv run pytest -q

format:
	UV_SYSTEM_PYTHON=1 uv run ruff format .

run:
	UV_SYSTEM_PYTHON=1 uv run fastapi run main:app --host 0.0.0.0 --port 8080
