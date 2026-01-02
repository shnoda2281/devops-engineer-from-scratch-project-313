SHELL := /bin/sh

.PHONY: setup install lint test format run

# Установка зависимостей строго по lock-файлу в system-python (без venv)
setup:
	uv sync --system --frozen

install: setup

# Линтер (ruff должен быть в dependencies или tools в pyproject.toml)
lint:
	uv run --system ruff check .

# Тесты
test:
	uv run --system pytest -q

# (опционально) форматирование
format:
	uv run --system ruff format .

# (опционально) локальный запуск приложения
run:
	uv run --system fastapi run main:app --host 0.0.0.0 --port 8080
