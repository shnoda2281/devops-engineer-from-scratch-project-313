# Базовый образ с Python
FROM python:3.12-slim

# Отключаем буферизацию вывода Python
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем curl и nginx
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl nginx \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Ставим Python-зависимости из uv.lock
RUN uv sync --frozen --no-cache --no-dev

# Копируем код приложения и nginx-конфиги
COPY . .

# ВАЖНО: выпиливаем дефолтный сайт nginx
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf || true

# Подключаем наш конфиг
COPY nginx/default.conf /etc/nginx/conf.d/app.conf

# Nginx слушает 80 (Render PORT=80)
EXPOSE 80

# Запускаем nginx и бэкенд
CMD ["sh", "-c", "service nginx start && uv run fastapi run --host 0.0.0.0 --port 8080"]
