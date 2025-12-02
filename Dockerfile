# Базовый образ с Python
FROM python:3.12-slim

# Отключаем буферизацию вывода Python
ENV PYTHONUNBUFFERED=1

# Рабочая директория
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

# Устанавливаем Python-зависимости (из uv.lock)
RUN uv sync --frozen --no-cache --no-dev

# Копируем приложение (код, тесты, nginx-конфиг и т.п.)
COPY . .

# Кладём наш конфиг nginx вместо дефолтного
# nginx/default.conf должен быть в репозитории
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Nginx будет слушать 80 (Render смотрит на PORT=80)
EXPOSE 80

# Запускаем nginx и FastAPI
CMD ["sh", "-c", "service nginx start && uv run fastapi run --host 0.0.0.0 --port 8080"]
