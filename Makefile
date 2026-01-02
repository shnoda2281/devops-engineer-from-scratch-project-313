.PHONY: setup install dev run lint format test check

# Hexlet вызывает именно: docker compose run app make setup
# В CI/контейнере venv не нужен
setup:
	UV_PYTHON_DOWNLOADS=never uv sync --system --frozen

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
	PYTHONPATH=. uv run pytest -q

check: lint test
