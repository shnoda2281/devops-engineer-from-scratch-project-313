FROM python:3.14-alpine

RUN apk add --no-cache build-base curl git bash make nodejs npm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /project

# чтобы uv не скачивал свой CPython
ENV UV_PYTHON_DOWNLOADS=never

# зависимости (кешируем лучше)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --system --frozen

# node deps (если нужны)
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# код
COPY . .

EXPOSE 8080
CMD ["uv", "run", "fastapi", "run", "main:app", "--host", "0.0.0.0", "--port", "8080"]
