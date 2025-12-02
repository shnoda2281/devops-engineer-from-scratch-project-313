import os
import logging
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel, Field, select

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# ------------------------------------------------------------------------------
# Инициализация логирования и Sentry
# ------------------------------------------------------------------------------

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[sentry_logging])
    logger.info("Sentry успешно подключён")

# ------------------------------------------------------------------------------
# Подключение к базе данных
# ------------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# Настройки движка SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)

# Фабрика сессий
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    """Отдаёт новую сессию БД для каждого запроса."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ------------------------------------------------------------------------------
# Определение моделей (SQLModel)
# ------------------------------------------------------------------------------

class LinkBase(SQLModel):
    """Базовая модель: поля, которые используются и при создании, и при чтении."""
    original_url: str
    short_name: str


class Link(LinkBase, table=True):
    """Табличная модель. extend_existing=True защищает от повторной регистрации таблицы."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)


class LinkCreate(LinkBase):
    """Модель для входящих данных при создании записи."""
    pass


class LinkUpdate(SQLModel):
    """Модель для обновления полей ссылки."""
    original_url: Optional[str] = None
    short_name: Optional[str] = None


class LinkRead(LinkBase):
    """Модель, которая отдаётся наружу API."""
    id: int
    short_url: Optional[str] = None


# ------------------------------------------------------------------------------
# Вспомогательная логика
# ------------------------------------------------------------------------------

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")


def build_short_url(short_name: str) -> str:
    """Формирует полный короткий URL."""
    return f"{BASE_URL}/r/{short_name}" if BASE_URL else short_name


# ------------------------------------------------------------------------------
# Инициализация FastAPI
# ------------------------------------------------------------------------------

app = FastAPI(title="URL Shortener")

# CORS — если будешь подключать фронт
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Создание таблиц при старте
# ------------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    logger.info("Создание таблиц (если отсутствуют)")
    SQLModel.metadata.create_all(engine)


# ------------------------------------------------------------------------------
# Технический эндпоинт для проверки
# ------------------------------------------------------------------------------

@app.get("/ping")
def ping():
    """Простой healthcheck."""
    return {"status": "ok", "timestamp": time.time()}


# ------------------------------------------------------------------------------
# CRUD API для коротких ссылок
# ------------------------------------------------------------------------------

@app.get("/api/links", response_model=list[LinkRead])
def list_links(session: Session = Depends(get_session)):
    """Возвращает список всех ссылок."""
    links = session.exec(select(Link)).all()
    return [
        LinkRead(
            id=link.id,
            original_url=link.original_url,
            short_name=link.short_name,
            short_url=build_short_url(link.short_name),
        )
        for link in links
    ]


@app.post("/api/links", response_model=LinkRead, status_code=201)
def create_link(data: LinkCreate, session: Session = Depends(get_session)):
    """Создаёт новую короткую ссылку."""
    link = Link.from_orm(data)
    session.add(link)
    session.commit()
    session.refresh(link)
    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.get("/api/links/{link_id}", response_model=LinkRead)
def get_link(link_id: int, session: Session = Depends(get_session)):
    """Возвращает одну ссылку по ID."""
    link = session.get(Link, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.put("/api/links/{link_id}", response_model=LinkRead)
def update_link(
    link_id: int, data: LinkUpdate, session: Session = Depends(get_session)
):
    """Обновляет запись: частично или полностью."""
    link = session.get(Link, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(link, field, value)

    session.add(link)
    session.commit()
    session.refresh(link)

    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.delete("/api/links/{link_id}", status_code=204)
def delete_link(link_id: int, session: Session = Depends(get_session)):
    """Удаляет ссылку по ID."""
    link = session.get(Link, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    session.delete(link)
    session.commit()
    return None


# ------------------------------------------------------------------------------
# Эндпоинт редиректа короткой ссылки
# ------------------------------------------------------------------------------

@app.get("/r/{short_name}")
def redirect_to_original(short_name: str, session: Session = Depends(get_session)):
    """Редирект по короткому имени."""
    link = session.exec(select(Link).where(Link.short_name == short_name)).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return RedirectResponse(link.original_url)
