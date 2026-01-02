SHELL := /bin/bash

.PHONY: setup lint test

setup:
	UV_SYSTEM_PYTHON=1 UV_PYTHON_DOWNLOADS=never uv sync --system --frozen

lint:
	uv run ruff check .

test:
	uv run pytest -q
