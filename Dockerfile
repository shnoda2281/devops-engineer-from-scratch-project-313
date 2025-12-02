FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    nginx \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s $HOME/.local/bin/uv /usr/local/bin/uv

# Python зависимости
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# Фронтенд
COPY package.json package-lock.json* ./
RUN npm install

# Копируем проект
COPY . .

# Собираем UI (dist)
RUN mkdir -p /usr/share/nginx/html \
    && cp -r node_modules/@hexlet/project-devops-deploy-crud-frontend/dist/* /usr/share/nginx/html/

# Nginx конфиг
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Порт, который будет слушать контейнер
EXPOSE 80

# Главная команда
CMD uv run fastapi run --host 0.0.0.0 --port 8080 & nginx -g "daemon off;"
