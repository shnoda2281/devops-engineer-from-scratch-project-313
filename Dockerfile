# Dockerfile
FROM python:3.12-slim

WORKDIR /project

# Чтобы uv НЕ скачивал питон и не создавал свой venv
ENV UV_SYSTEM_PYTHON=1 \
    UV_PYTHON_DOWNLOADS=never \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Пакеты для сборки зависимостей + node/npm (у тебя npm используется)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl git bash make nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# ruff (как и было у тебя в логах)
RUN uv tool install ruff@latest

# npm deps (если реально нужны в проекте)
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# проект
COPY . .
