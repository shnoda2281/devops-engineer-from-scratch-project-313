FROM python:3.14-slim

# Неинтерактивный режим apt
ENV DEBIAN_FRONTEND=noninteractive

# Ставим системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    make \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Обновляем pip и ставим uv
RUN python -m pip install --upgrade pip \
 && python -m pip install uv

# Копируем файлы зависимостей отдельно — для кеша
COPY pyproject.toml uv.lock ./

# ⚠️ ВАЖНО:
# Устанавливаем зависимости В СИСТЕМУ, БЕЗ virtualenv
RUN uv sync --system --frozen

# Копируем приложение
COPY . .

# Конфиг nginx
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Удаляем дефолтный сайт nginx
RUN rm -f /etc/nginx/sites-enabled/default || true

# Render / prod
ENV PORT=80
EXPOSE 80

# Запуск backend + nginx
CMD uv run fastapi run main:app --host 0.0.0.0 --port 8080 & \
    nginx -g 'daemon off;'
