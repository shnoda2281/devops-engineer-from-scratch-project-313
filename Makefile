.PHONY: install setup dev run lint format test

# Устанавливает зависимости через uv (создаёт .venv на базе pyproject.toml / uv.lock)
install:
	uv sync

# Нужна для Hexlet-action: он вызывает `make setup`
setup: install

# Локальная разработка
dev:
	uv run fastapi dev --host 0.0.0.0 --port 8080

# Просто синоним dev (по требованиям проекта)
run:
	uv run fastapi dev --host 0.0.0.0 --port 8080

# Линтер
lint:
	uv run ruff check .

# Автоформатирование
format:
	uv run ruff format .

# Тесты
test:
	uv run pytest
