SHELL := /bin/bash

.PHONY: setup lint test

setup:
	UV_PYTHON_DOWNLOADS=never uv sync --frozen --python python3.14

lint:
	uv run ruff check .

test:
	uv run pytest -q
