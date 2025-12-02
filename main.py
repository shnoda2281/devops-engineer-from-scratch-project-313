import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Annotated

import sentry_sdk
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlmodel import Field, Session, SQLModel, create_engine, select

# ------------------------ #
#       INITIAL SETUP      #
# ------------------------ #

load_dotenv()

logger = logging.getLogger("app")

# ------------------------ #
#       SENTRY INIT        #
# ------------------------ #

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

# ------------------------ #
#       DATABASE INIT      #
# ------------------------ #


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_db_url(
    os.getenv("DATABASE_URL", "sqlite:///./dev.db")
)

engine = create_engine(DATABASE_URL, echo=False)


class LinkBase(SQLModel):
    original_url: str
    short_name: str


class Link(LinkBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    __table_args__ = {"extend_existing": True}


class LinkCreate(LinkBase):
    ...


class LinkUpdate(SQLModel):
    original_url: str | None = None
    short_name: str | None = None


class LinkRead(LinkBase):
    id: int
    short_url: str


def get_base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")


def get_session() -> Session:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
BaseURLDep = Annotated[str, Depends(get_base_url)]

# ------------------------ #
#         LIFESPAN         #
# ------------------------ #


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


# ------------------------ #
#         APP SETUP        #
# ------------------------ #

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ------------------------ #
#           CRUD           #
# ------------------------ #


def build_short_url(base_url: str, short_name: str) -> str:
    return f"{base_url}/r/{short_name}"


@app.get("/api/links", response_model=list[LinkRead])
def list_links(session: SessionDep, base_url: BaseURLDep):
    links = session.exec(select(Link)).all()
    return [
        LinkRead(
            id=link.id,
            original_url=link.original_url,
            short_name=link.short_name,
            short_url=build_short_url(base_url, link.short_name),
        )
        for link in links
    ]


@app.post("/api/links", response_model=LinkRead, status_code=status.HTTP_201_CREATED)
def create_link(payload: LinkCreate, session: SessionDep, base_url: BaseURLDep):
    existing = session.exec(
        select(Link).where(Link.short_name == payload.short_name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Short name already exists",
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
        short_url=build_short_url(base_url, link.short_name),
    )


@app.get("/api/links/{link_id}", response_model=LinkRead)
def get_link(link_id: int, session: SessionDep, base_url: BaseURLDep):
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
        short_url=build_short_url(base_url, link.short_name),
    )


@app.put("/api/links/{link_id}", response_model=LinkRead)
def update_link(
    link_id: int,
    payload: LinkUpdate,
    session: SessionDep,
    base_url: BaseURLDep,
):
    link = session.get(Link, link_id)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    if payload.short_name and payload.short_name != link.short_name:
        existing = session.exec(
            select(Link).where(Link.short_name == payload.short_name)
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Short name already exists",
            )

        link.short_name = payload.short_name

    if payload.original_url:
        link.original_url = payload.original_url

    session.add(link)
    session.commit()
    session.refresh(link)

    return LinkRead(
        id=link.id,
        original_url=link.original_url,
        short_name=link.short_name,
        short_url=build_short_url(base_url, link.short_name),
    )


@app.delete("/api/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: int, session: SessionDep):
    link = session.get(Link, link_id)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    session.delete(link)
    session.commit()
    return None


# ------------------------ #
#     SERVICE ENDPOINTS    #
# ------------------------ #


@app.get("/ping")
def ping():
    return "pong"


@app.get("/error")
def error():
    raise RuntimeError("Test error for Sentry")
