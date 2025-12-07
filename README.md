### Hexlet tests and linter status

[![Hexlet Status](https://github.com/shnoda2281/devops-engineer-from-scratch-project-313/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/shnoda2281/devops-engineer-from-scratch-project-313/actions/workflows/hexlet-check.yml)

![CI](https://github.com/shnoda2281/devops-engineer-from-scratch-project-313/actions/workflows/ci.yml/badge.svg)

# FastAPI приложение

Небольшое приложение на FastAPI для демонстрации базового запуска, тестирования, CI и деплоя с использованием Nginx и Render.  
Приложение содержит простой API и веб-интерфейс.

---

## Стек

- Python 3.12+
- FastAPI / Uvicorn
- PostgreSQL (в продакшене)
- Nginx (как reverse-proxy и раздача статики)
- Docker + Dockerfile
- GitHub Actions (CI + hexlet-check)
- Render (деплой)

---

## Требования для локального запуска

- Python 3.12+
- Установленный [uv](https://github.com/astral-sh/uv)
- Docker (для проверки Dockerfile при необходимости)

---

## Установка и запуск локально

```bash
# Установка зависимостей
make install

# Запуск линтера
make lint

# Запуск тестов
make test

# Локальный запуск приложения (без Docker)
make dev
