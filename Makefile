SHELL := /bin/bash

.PHONY: setup lint test

# ВАЖНО: --system = ставим зависимости в системный python контейнера
# --frozen = требуем актуальный lock (uv.lock). Если lock ещё нет — временно убери --frozen.
setup:
	cd code && UV_SYSTEM_PYTHON=1 UV_PYTHON_DOWNLOADS=never uv sync --system --frozen

lint:
	cd code && uv run ruff check .

test:
	cd code && uv run pytest -q
