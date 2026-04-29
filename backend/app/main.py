"""FastAPI application entrypoint."""

import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    setup_logging()
    log = structlog.get_logger()
    log.info("settle_starting", version="0.1.0")
    yield
    log.info("settle_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Inject a unique request_id into structlog context for every request."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# --- Health endpoints ---

@app.get("/api/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Liveness probe — app is running."""
    return {"status": "ok"}


@app.get("/api/health/ready", tags=["health"])
async def health_ready() -> dict[str, str]:
    """Readiness probe — app can serve requests.

    Full DB check will be added when database models are in place (stage 2).
    """
    return {"status": "ok"}
