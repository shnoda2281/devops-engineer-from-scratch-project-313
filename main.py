import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------
# Sentry
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# DB URL Normalization
# ---------------------------------------------------------
def _normalize_db_url(url: str) -> str:
    """
    Render DB URL может быть в двух форматах:
    - postgres://...
    - postgresql://...
    Приводим оба к psycopg-драйверу: postgresql+psycopg://
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./dev.db"))
engine = create_engine(DATABASE_URL, echo=False)


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class LinkBase(SQLModel):
    original_url: str
    short_name: str = Field(index=True)


# При повторном импорте модуля в тестах таблица уже может быть зарегистрирована
if "link" in SQLModel.metadata.tables:
    SQLModel.metadata.remove(SQLModel.metadata.tables["link"])


class Link(LinkBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class LinkCreate(BaseModel):
    original_url: str
    short_name: str


class LinkRead(LinkBase):
    id: int
    short_url: str


# ---------------------------------------------------------
# Lifespan → Auto-migrations
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Middleware logging
# ---------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000

    logger.info(
        "%s %s completed_in=%.2fms status=%s",
        request.method,
        request.url.path,
        duration,
        response.status_code,
    )
    return response


# ---------------------------------------------------------
# /ping
# ---------------------------------------------------------
@app.get("/ping")
def ping():
    return "pong"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def build_short_url(short_name: str) -> str:
    base = os.getenv("BASE_URL", "http://localhost:8080")
    return f"{base}/r/{short_name}"


# ---------------------------------------------------------
# CRUD API
# ---------------------------------------------------------
# (1) GET /api/links
@app.get("/api/links", response_model=list[LinkRead])
def list_links():
    with Session(engine) as session:
        links = session.exec(select(Link)).all()
        return [
            LinkRead(
                id=link_obj.id,
                original_url=link_obj.original_url,
                short_name=link_obj.short_name,
                short_url=build_short_url(link_obj.short_name),
            )
            for link_obj in links
        ]


# (2) POST /api/links
@app.post("/api/links", response_model=LinkRead, status_code=status.HTTP_201_CREATED)
def create_link(payload: LinkCreate):
    with Session(engine) as session:
        existing = session.exec(
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
        session.add(link)
        session.commit()
        session.refresh(link)

        return LinkRead(
            id=link.id,
            original_url=link.original_url,
            short_name=link.short_name,
            short_url=build_short_url(link.short_name),
        )


# (3) GET /api/links/:id
@app.get("/api/links/{link_id}", response_model=LinkRead)
def get_link(link_id: int):
    with Session(engine) as session:
        link = session.get(Link, link_id)
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


# (4) PUT /api/links/:id
@app.put("/api/links/{link_id}", response_model=LinkRead)
def update_link(link_id: int, payload: LinkCreate):
    with Session(engine) as session:
        link = session.get(Link, link_id)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        if payload.short_name != link.short_name:
            existing = session.exec(
                select(Link).where(Link.short_name == payload.short_name),
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="short_name already exists",
                )

        link.original_url = payload.original_url
        link.short_name = payload.short_name

        session.add(link)
        session.commit()
        session.refresh(link)

        return LinkRead(
            id=link.id,
            original_url=link.original_url,
            short_name=link.short_name,
            short_url=build_short_url(link.short_name),
        )


# (5) DELETE /api/links/:id
@app.delete("/api/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: int):
    with Session(engine) as session:
        link = session.get(Link, link_id)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        session.delete(link)
        session.commit()
        return None


# ---------------------------------------------------------
# /error (test Sentry)
# ---------------------------------------------------------
@app.get("/error")
def error():
    raise RuntimeError("Test Sentry error")
