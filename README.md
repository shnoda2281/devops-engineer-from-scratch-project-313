### Hexlet tests and linter status:
[![Actions Status](https://github.com/shnoda2281/devops-engineer-from-scratch-project-313/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/shnoda2281/devops-engineer-from-scratch-project-313/actions)
# FastAPI приложение

![CI](https://github.com/shnoda2281/devops-engineer-from-scratch-project-313/actions/workflows/ci.yml/badge.svg)
Небольшое приложение на FastAPI для демонстрации базового запуска и настройки middleware.

## Требования

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) установлен в системе

## Установка

```bash
make install

## Развернутое приложение

Приложение доступно по адресу:

https://devops-engineer-from-scratch-project-313-5iro.onrender.com

### Примеры запросов:
- `GET /ping` → `"pong"`
- `GET /error` → генерирует тестовую ошибку, отправляется в Sentry
