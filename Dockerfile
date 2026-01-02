FROM python:3.14-alpine

RUN apk add --no-cache \
    build-base \
    curl \
    git \
    bash \
    make \
    nodejs \
    npm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=never
ENV UV_SYSTEM_PYTHON=1

WORKDIR /project

# Python deps (из code/)
COPY code/pyproject.toml code/uv.lock ./code/
RUN --mount=type=cache,target=/root/.cache/uv \
    cd code && uv sync --system --frozen

# Node deps (если package*.json в корне)
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Исходники
COPY . .

WORKDIR /project/code

EXPOSE 8080
CMD ["uv", "run", "--system", "fastapi", "run", "main:app", "--host", "0.0.0.0", "--port", "8080"]
