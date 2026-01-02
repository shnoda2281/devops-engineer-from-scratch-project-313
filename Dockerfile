FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Системные зависимости
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx \
        curl \
        make \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Копируем файлы зависимостей отдельно (кеш слоёв)
COPY pyproject.toml uv.lock ./

# Установка зависимостей БЕЗ virtualenv (важно для CI/Hexlet)
RUN uv sync --frozen --no-venv

# Копируем весь проект
COPY . .

# Nginx config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default || true

EXPOSE 80

# Backend на 8080, nginx на 80
CMD uv run fastapi run main:app --host 0.0.0.0 --port 8080 & \
    nginx -g 'daemon off;'
