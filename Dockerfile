# Dockerfile
FROM python:3.14-slim

WORKDIR /project

# ВАЖНО: запрещаем uv скачивать интерпретатор
ENV UV_PYTHON_DOWNLOADS=never \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# системные зависимости + node/npm (если используется в проекте)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl git bash make nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# ruff (как в твоём пайплайне)
RUN uv tool install ruff@latest

# npm deps (если package-lock.json реально есть — у тебя он есть)
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# проект
COPY . .
