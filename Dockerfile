# Базовый образ с Python
FROM python:3.12-slim

# Отключаем буферизацию выводов Python
ENV PYTHONUNBUFFERED=1

# Рабочая директория
WORKDIR /app

# Установка uv
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s $HOME/.local/bin/uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости (флаг --frozen гарантирует что используется uv.lock)
RUN uv sync --frozen --no-cache

# Копируем код
COPY . .

# EXPOSE по желанию (Render сам использует PORT)
EXPOSE 8080

# Запуск приложения
CMD ["uv", "run", "fastapi", "run", "--host", "0.0.0.0", "--port", "8080"]
