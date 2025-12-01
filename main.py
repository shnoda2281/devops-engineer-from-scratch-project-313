import logging
import os
import time

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger("app")

# Получаем DSN из переменной окружения
SENTRY_DSN = os.getenv("SENTRY_DSN")

# Инициализируем Sentry, ТОЛЬКО если DSN корректный
# (локально SENTRY_DSN обычно отсутствует → Sentry не включается → pytest не ломается)
if SENTRY_DSN and SENTRY_DSN.startswith("http"):
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # какие логи писать в логгер
        event_level=logging.ERROR, # какие отправлять в Sentry
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=1.0,
    )

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в проде лучше ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Логирование запросов ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = (time.time() - start) * 1000

    logger.info(
        "%s %s completed_in=%.2fms status=%s",
        request.method,
        request.url.path,
        process_time,
        response.status_code,
    )

    return response


# --- /ping ---
@app.get("/ping")
def ping():
    return "pong"


# --- /error для теста Sentry ---
@app.get("/error")
def error():
    # Эту ошибку увидишь в Sentry ТОЛЬКО на Render (где SENTRY_DSN задан)
    raise RuntimeError("Test error for Sentry")
