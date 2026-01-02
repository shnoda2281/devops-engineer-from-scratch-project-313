.PHONY: install dev run lint format test setup

# Hexlet вызывает именно ЭТО
# В контейнерах и CI virtualenv НЕ нужен
setup:
	uv sync --system --no-cache

# Локальная установка (аналогично)
install: setup

dev:
	uv run fastapi dev --host 0.0.0.0 --port 8080

run:
	uv run fastapi run main:app --host 0.0.0.0 --port 8080

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest
