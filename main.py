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
logging.basicConfig(level=logging.INFO)

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), sentry_logging],
        traces_sample_rate=1.0,
    )

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

engine = create_engine(DATABASE_URL, echo=False)


def build_short_url(short_name: str) -> str:
    base = BASE_URL.rstrip("/")
    return f"{base}/r/{short_name}"


class LinkBase(SQLModel):
    original_url: str
    short_name: str


class Link(LinkBase, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)


class LinkCreate(LinkBase):
    pass


class LinkUpdate(SQLModel):
    original_url: Optional[str] = None
    short_name: Optional[str] = None


class LinkRead(LinkBase):
    id: int
    short_url: str


def get_db() -> Session:
    with Session(engine) as session:
        yield session


app = FastAPI()

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range"],
)


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized")


@app.get("/ping")
def ping() -> str:
    return "pong"


@app.get("/r/{short_name}", response_class=RedirectResponse)
def redirect_to_original(
    short_name: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Редирект по короткой ссылке на оригинальный URL."""
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


@app.get("/api/links", response_model=list[LinkRead])
def list_links(
    response: Response,
    range_param: str = Query(
        default="[0,9]",
        alias="range",
        description="Диапазон элементов, например [0,9]",
    ),
    db: Session = Depends(get_db),
) -> list[LinkRead]:
    """Список ссылок с поддержкой пагинации через range-параметр."""
    try:
        start_str, end_str = range_param.strip("[]").split(",")
        start = int(start_str)
        end = int(end_str)
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
    total_links = db.exec(select(Link)).all()
    total_count = len(total_links)

    # Пагинированный список
    limit = end - start + 1
    statement = select(Link).offset(start).limit(limit)
    links = db.exec(statement).all()

    if links:
        content_start = start
        content_end = start + len(links) - 1
        content_range = f"links {content_start}-{content_end}/{total_count}"
    else:
        content_range = f"links */{total_count}"

    response.headers["Content-Range"] = content_range

    return [
        LinkRead(
            id=link.id,
            original_url=link.original_url,
            short_name=link.short_name,
            short_url=build_short_url(link.short_name),
        )
        for link in links
    ]


@app.post(
    "/api/links",
    response_model=LinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_link(
    payload: LinkCreate,
    db: Session = Depends(get_db),
) -> LinkRead:
    """Создание короткой ссылки."""
    statement = select(Link).where(Link.short_name == payload.short_name)
    existing = db.exec(statement).first()
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
    """Получение одной ссылки по id."""
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

    # Проверяем конфликт short_name, если его меняем
    if payload.short_name and payload.short_name != link.short_name:
        statement = select(Link).where(Link.short_name == payload.short_name)
        conflict = db.exec(statement).first()
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


@app.delete(
    "/api/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Удаление ссылки по id."""
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    db.delete(link)
    db.commit()
