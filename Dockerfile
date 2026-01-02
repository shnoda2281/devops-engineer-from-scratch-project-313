FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Минимум системных зависимостей
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем uv
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir uv

# Зависимости отдельно — для кеша
COPY pyproject.toml uv.lock ./

# ВАЖНО: без virtualenv
RUN uv sync --no-venv --frozen

# Код приложения
COPY . .

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
