FROM python:3.12-slim

# Неинтерактивный режим apt
ENV DEBIAN_FRONTEND=noninteractive

# Ставим nginx, curl и make (make нужен для docker compose run app make ...)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx curl make \
    && rm -rf /var/lib/apt/lists/*

# Обновляем pip и ставим uv
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir uv

WORKDIR /app

# Копируем файлы зависимостей отдельно — для кеша
COPY pyproject.toml uv.lock ./

# Установим зависимости (создаст .venv внутри контейнера)
RUN uv sync --frozen

# Копируем всё приложение
COPY . .

# Кладём наш конфиг nginx
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# На всякий случай удалим дефолтный сайт nginx, если он есть
RUN rm -f /etc/nginx/sites-enabled/default || true

# Nginx слушает 80, Render пробрасывает PORT=80
ENV PORT=80
EXPOSE 80

# Стартуем backend на 8080 и nginx на 80
CMD uv run fastapi run main:app --host 0.0.0.0 --port 8080 & \
    nginx -g 'daemon off;'
