import logging
import os
import time
from typing import Optional

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ----------------------------
# Sentry
# ----------------------------

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[sentry_logging])

logger = logging.getLogger("app")


# ----------------------------
# DB
# ----------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=False)


def get_db():
    """Создаёт сессию БД и закрывает её после запроса."""
    with Session(engine) as session:
        yield session


# ----------------------------
# Models
# ----------------------------

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


# ----------------------------
# App
# ----------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ----------------------------
# Startup event
# ----------------------------

@app.on_event("startup")
def startup():
    """Создание таблиц при запуске приложения."""
    time.sleep(0.1)
    SQLModel.metadata.create_all(engine)


# ----------------------------
# Healthcheck
# ----------------------------

@app.get("/ping")
def ping():
    return "pong"


# ----------------------------
# Utils
# ----------------------------

def build_short_url(short_name: str) -> str:
    base = os.getenv("BASE_URL", "http://localhost:8000")
    return f"{base}/r/{short_name}"


# ----------------------------
# CRUD
# ----------------------------

@app.get("/api/links", response_model=list[LinkRead])
def list_links(db: Session = Depends(get_db)):
    items = db.exec(select(Link)).all()
    return [
        LinkRead(
            id=i.id,
            original_url=i.original_url,
            short_name=i.short_name,
            short_url=build_short_url(i.short_name),
        )
        for i in items
    ]


@app.post("/api/links", response_model=LinkRead, status_code=201)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)):
    exists = db.exec(
        select(Link).where(Link.short_name == payload.short_name),
    ).first()

    if exists:
        raise HTTPException(400, "short_name already exists")

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
def get_link(link_id: int, db: Session = Depends(get_db)):
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(404, "Link not found")

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
        raise HTTPException(404, "Link not found")

    if payload.short_name and payload.short_name != link.short_name:
        conflict = db.exec(
            select(Link).where(Link.short_name == payload.short_name),
        ).first()
        if conflict:
            raise HTTPException(400, "short_name already exists")

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


@app.delete("/api/links/{link_id}", status_code=204)
def delete_link(link_id: int, db: Session = Depends(get_db)):
    link = db.get(Link, link_id)
    if not link:
        raise HTTPException(404, "Link not found")

    db.delete(link)
    db.commit()
    return


@app.get("/r/{short_name}")
def redirect_short(short_name: str, db: Session = Depends(get_db)):
    link = db.exec(
        select(Link).where(Link.short_name == short_name),
    ).first()

    if not link:
        raise HTTPException(404, "Link not found")

    return RedirectResponse(link.original_url)
