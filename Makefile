.PHONY: install dev run lint test

# Установка зависимостей (по pyproject.toml)
install:
	uv sync

# Запуск приложения разработки
dev:
	uv run fastapi dev --host 0.0.0.0 --port 8080

# Альтернативная команда с тем же запуском (если нужно явно)
run:
	uv run fastapi dev --host 0.0.0.0 --port 8080

# На будущее — линтеры/тесты (если будут)
lint:
	uv run ruff check .

test:
	uv run pytest
