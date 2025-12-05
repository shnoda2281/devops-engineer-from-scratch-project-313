FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем nginx
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

# Ставим зависимости проекта
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Кладём весь код внутрь образа
COPY . .

# Подменяем главный конфиг nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Nginx будет слушать 80 порт
EXPOSE 80

# Запускаем бэкенд и nginx
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 3000 & nginx -g 'daemon off;'"]
