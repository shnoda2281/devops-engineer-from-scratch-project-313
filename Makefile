.PHONY: setup install dev run lint format test

# Установка uv (если его нет) и зависимостей проекта
setup:
	python -m pip install --upgrade pip
	python -m pip install uv
	uv sync --frozen

# Алиас (Hexlet иногда вызывает install)
install: setup

# Запуск приложения для разработки
dev:
	uv run fastapi dev --host 0.0.0.0 --port 8080

# Запуск приложения (то же самое, но без "dev"-алиаса)
run:
	uv run fastapi dev --host 0.0.0.0 --port 8080

# Запуск линтера
lint:
	uv run ruff check .

# Автоформатирование
format:
	uv run ruff format .

# Запуск тестов
test:
	uv run pytest
