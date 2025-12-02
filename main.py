import logging
import os
from typing import Optional

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlmodel import Field, Session, SQLModel, create_engine, select
from starlette import status

logger = logging.getLogger("app")

app = FastAPI()

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN and SENTRY_DSN.startswith("http"):
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), sentry_logging],
        traces_sample_rate=1.0,
    )

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=False)


class LinkBase(SQLModel):
    original_url: str
    short_name: str


class Link(LinkBase, table=True):
    __tablename__ = "link"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)


class LinkRead(LinkBase):
    id: int
    short_url: str


class LinkCreate(LinkBase):
    pass


class LinkUpdate(SQLModel):
    original_url: Optional[str] = None
    short_name: Optional[str] = None


def get_base_url() -> str:
    """Базовый адрес сервиса для формирования short_url."""
    return os.getenv("BASE_URL", "http://localhost:8080")


def build_short_url(short_name: str) -> str:
    return f"{get_base_url().rstrip('/')}/r/{short_name}"


def get_db() -> Session:
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized")


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Важно: фронтенду надо видеть заголовок Content-Range
    expose_headers=["Content-Range"],
)

# ---------------------------------------------------------------------------
# Middleware логирования
# ---------------------------------------------------------------------------


@app.middleware("http")
async def log_requests(request, call_next):
    logger.info("Request: %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("Response: %s %s", request.method, response.status_code)
    return response


# ---------------------------------------------------------------------------
# Healthcheck / Sentry test
# ---------------------------------------------------------------------------


@app.get("/ping")
def ping() -> str:
    return "pong"


@app.get("/error")
def error() -> None:
    raise RuntimeError("Test error for Sentry")


# ---------------------------------------------------------------------------
# Redirect endpoint
# ---------------------------------------------------------------------------


@app.get("/r/{short_name}", response_class=RedirectResponse)
def redirect_to_original(
    short_name: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Редирект по короткому имени на оригинальный URL."""
    statement = select(Link).where(Link.short_name == short_name)
    link = db.exec(statement).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    return RedirectResponse(
        url=link.original_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


# ---------------------------------------------------------------------------
# CRUD + пагинация
# ---------------------------------------------------------------------------


@app.get("/api/links", response_model=list[LinkRead])
def list_links(
    response: Response,
    range_param: str = Query(default="[0,9]", alias="range"),
    db: Session = Depends(get_db),
) -> list[LinkRead]:
    """
    Список ссылок с пагинацией.

    Ожидает параметр ?range=[start,end] и возвращает заголовок:
    Content-Range: links start-end/total
    """
    import json

    try:
        start, end = json.loads(range_param)
        start = int(start)
        end = int(end)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range format",
        ) from exc

    if start < 0 or end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range values",
        )

    # Общее количество записей
    all_links = db.exec(select(Link)).all()
    total = len(all_links)

    # Получаем нужный срез
    limit = end - start + 1
    statement = select(Link).offset(start).limit(limit)
    links = db.exec(statement).all()

    if total == 0:
        content_range_value = "links 0-0/0"
    else:
        last_index = start + max(len(links) - 1, 0)
        content_range_value = f"links {start}-{last_index}/{total}"

    response.headers["Content-Range"] = content_range_value

    return [
        LinkRead(
            id=link.id,
            original_url=link.original_url,
            short_name=link.short_name,
            short_url=build_short_url(link.short_name),
        )
        for link in links
    ]


@app.post("/api/links", response_model=LinkRead, status_code=status.HTTP_201_CREATED)
def create_link(
    payload: LinkCreate,
    db: Session = Depends(get_db),
) -> LinkRead:
    """Создание короткой ссылки."""
    existing = db.exec(
        select(Link).where(Link.short_name == payload.short_name),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="short_name already exists",
        )

    link = Link(
        original_url=payload.original_url,
        short_name=payload.short_name,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.get("/api/links/{link_id}", response_model=LinkRead)
def get_link(
    link_id: int,
    db: Session = Depends(get_db),
) -> LinkRead:
    """Получение ссылки по id."""
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.put("/api/links/{link_id}", response_model=LinkRead)
def update_link(
    link_id: int,
    payload: LinkUpdate,
    db: Session = Depends(get_db),
) -> LinkRead:
    """Полное обновление ссылки."""
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    # Проверяем конфликт short_name, если его поменяли
    if payload.short_name and payload.short_name != link.short_name:
        conflict = db.exec(
            select(Link).where(Link.short_name == payload.short_name),
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="short_name already exists",
            )

    if payload.original_url is not None:
        link.original_url = payload.original_url
    if payload.short_name is not None:
        link.short_name = payload.short_name

    db.add(link)
    db.commit()
    db.refresh(link)

    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.delete("/api/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Удаление ссылки."""
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    db.delete(link)
    db.commit()
