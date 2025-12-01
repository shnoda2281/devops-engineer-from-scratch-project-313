from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

logger = logging.getLogger("app")

app = FastAPI()


# --- CORS middleware для локальной разработки ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # в проде лучше ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Простое логирование запросов ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    logger.info(
        "%s %s completed_in=%.2fms status_code=%s",
        request.method,
        request.url.path,
        process_time,
        response.status_code,
    )

    return response


# --- Маршрут /ping ---
@app.get("/ping")
def ping():
    return "pong"
