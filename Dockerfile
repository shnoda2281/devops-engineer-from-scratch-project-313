FROM python:3.14-alpine

# системные пакеты (добавь что надо под твои либы)
RUN apk add --no-cache \
    build-base curl git bash make nodejs npm

# uv бинарники
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /project

# быстрее кешится
COPY pyproject.toml uv.lock ./

# запретить uv скачивать питон
ENV UV_PYTHON_DOWNLOADS=never

# поставить зависимости в system (без venv)
RUN uv sync --system --frozen

# остальное
COPY . .

EXPOSE 8080

CMD ["uv", "run", "fastapi", "run", "main:app", "--host", "0.0.0.0", "--port", "8080"]
