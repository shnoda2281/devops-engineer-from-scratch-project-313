import logging
import os
from typing import Optional

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ------------------------------------------------------------------------------
# Логирование и Sentry
# ------------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[sentry_logging])

# ------------------------------------------------------------------------------
# Настройки приложения и БД
# ------------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

engine = create_engine(DATABASE_URL, echo=False)


def build_short_url(short_name: str) -> str:
    """Возвращает полный URL редиректа."""
    return f"{BASE_URL}/r/{short_name}"


# ------------------------------------------------------------------------------
# Модели
# ------------------------------------------------------------------------------

class LinkBase(SQLModel):
    original_url: str
    short_name: str


class Link(LinkBase, table=True):
    """Таблица Link в базе данных."""
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


# ------------------------------------------------------------------------------
# Инициализация БД при старте
# ------------------------------------------------------------------------------

app = FastAPI()


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized")


# ------------------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Работа с БД
# ------------------------------------------------------------------------------

def get_db():
    with Session(engine) as session:
        yield session


# ------------------------------------------------------------------------------
# Ping
# ------------------------------------------------------------------------------

@app.get("/ping")
def ping():
    return "pong"


# ------------------------------------------------------------------------------
# Range-парсер
# ------------------------------------------------------------------------------

def parse_range(value: str | None) -> tuple[int, int] | None:
    """Парсит '[start,end]' → tuple(start, end)."""
    if not value:
        return None

    try:
        raw = value.strip()
        if not raw.startswith("[") or not raw.endswith("]"):
            return None

        inner = raw[1:-1]
        start_str, end_str = inner.split(",")

        start = int(start_str.strip())
        end = int(end_str.strip())

        if start < 0 or end < start:
            return None

        return start, end
    except Exception:
        return None


# ------------------------------------------------------------------------------
# CRUD + пагинация
# ------------------------------------------------------------------------------

@app.get("/api/links", response_model=list[LinkRead])
def list_links(
    response: Response,
    range: str | None = Query(default=None, alias="range"),
    db: Session = Depends(get_db),
):
    total_rows = db.exec(select(Link)).all()
    total = len(total_rows)

    if total == 0:
        response.headers["Content-Range"] = "links */0"
        return []

    parsed = parse_range(range)

    if parsed:
        start, requested_end = parsed
        if start >= total:
            response.headers["Content-Range"] = f"links */{total}"
            return []

        end = min(requested_end, total - 1)
        limit = end - start + 1
        rows = db.exec(select(Link).offset(start).limit(limit)).all()
        end = start + len(rows) - 1
    else:
        start = 0
        end = total - 1
        rows = total_rows

    response.headers["Content-Range"] = f"links {start}-{end}/{total}"

    return [
        LinkRead(
            id=row.id,
            original_url=row.original_url,
            short_name=row.short_name,
            short_url=build_short_url(row.short_name),
        )
        for row in rows
    ]


@app.post("/api/links", response_model=LinkRead, status_code=201)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)):
    existing = db.exec(
        select(Link).where(Link.short_name == payload.short_name)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="short_name already exists")

    link = Link(**payload.__dict__)
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
def get_link(link_id: int, db: Session = Depends(get_db)):
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(link.short_name),
    )


@app.put("/api/links/{link_id}", response_model=LinkRead)
def update_link(link_id: int, payload: LinkUpdate, db: Session = Depends(get_db)):
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if payload.short_name and payload.short_name != link.short_name:
        conflict = db.exec(
            select(Link).where(Link.short_name == payload.short_name)
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="short_name already exists")

    if payload.original_url:
        link.original_url = payload.original_url
    if payload.short_name:
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


@app.delete("/api/links/{link_id}", status_code=204)
def delete_link(link_id: int, db: Session = Depends(get_db)):
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()


@app.get("/r/{short_name}")
def redirect_short(short_name: str, db: Session = Depends(get_db)):
    row = db.exec(select(Link).where(Link.short_name == short_name)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")

    return RedirectResponse(url=row.original_url)
