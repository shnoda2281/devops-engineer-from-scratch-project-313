FROM python:3.14-alpine

# Базовые пакеты для сборки wheels + node/npm (если нужны в проекте)
RUN apk add --no-cache \
    build-base \
    curl \
    git \
    bash \
    make \
    nodejs \
    npm

# uv бинарник (и uvx) из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /project

# Запрещаем uv скачивать другой Python (только системный из образа)
ENV UV_PYTHON_DOWNLOADS=never
# Гарантируем system mode (никаких venv)
ENV UV_SYSTEM_PYTHON=1

# Сначала lock/pyproject (для кеша слоёв)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --system --frozen

# Node deps (если реально используются)
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Код
COPY . .

EXPOSE 8080

CMD ["uv", "run", "--system", "fastapi", "run", "main:app", "--host", "0.0.0.0", "--port", "8080"]
