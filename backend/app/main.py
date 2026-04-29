"""FastAPI application entrypoint."""

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.api.routers.auth import router as auth_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.import_data import router as import_data_router
from app.api.routers.incomes import router as incomes_router
from app.api.routers.loans import router as loans_router
from app.api.routers.payments import router as payments_router
from app.api.routers.scenarios import router as scenarios_router
from app.api.routers.settings import router as settings_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import setup_logging
from app.core.metrics import instrumentator
from app.core.security import hash_password
from app.domain.models.user import User
from app.tasks.scheduler import start_scheduler, stop_scheduler

# Paths excluded from HTTP request logging (noisy / health probes).
_SILENT_PATHS = frozenset({"/api/health/live", "/api/health/ready", "/metrics"})


async def _seed_user() -> None:
    """Create the seed user from .env if not already present (idempotent)."""
    log = structlog.get_logger()
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == settings.seed_user_email)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            log.info("seed_user_exists", email=settings.seed_user_email)
            return

        user = User(
            email=settings.seed_user_email,
            password_hash=hash_password(settings.seed_user_password),
        )
        session.add(user)
        await session.commit()
        log.info("seed_user_created", email=settings.seed_user_email, user_id=str(user.id))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    setup_logging()
    log = structlog.get_logger()
    log.info("settle_starting", version="0.1.0")

    # Seed the default user
    await _seed_user()

    # Start background job scheduler
    await start_scheduler()


    yield

    # Stop scheduler on shutdown
    await stop_scheduler()
    log.info("settle_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# --- Prometheus instrumentation (must be before middleware registration) ---

instrumentator.instrument(app)
instrumentator.expose(app, include_in_schema=False, tags=["metrics"])

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Inject request_id and log every HTTP request with timing (§13.1).

    Binds request_id and optional user_id to structlog context.
    Logs path, method, status_code, duration_ms for every request
    (except health/metrics endpoints to reduce noise).
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.monotonic()
    response: Response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id

    path = request.url.path
    if path not in _SILENT_PATHS:
        # Try to extract user_id from request state (set by auth dependency)
        user_id = getattr(request.state, "user_id", None)
        log = structlog.get_logger("http")
        log.info(
            "http_request",
            path=path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=str(user_id) if user_id else None,
        )

    return response


# --- RFC 7807 error handling ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic validation errors to RFC 7807 format."""
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append({
            "field": field,
            "code": err["type"],
            "message": err["msg"],
        })
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://errors.settle/validation",
            "title": "Ошибка валидации",
            "status": 422,
            "detail": f"Обнаружено ошибок: {len(errors)}",
            "instance": str(request.url.path),
            "errors": errors,
        },
    )


# --- Routers ---

app.include_router(auth_router)
app.include_router(loans_router)
app.include_router(payments_router)
app.include_router(incomes_router)
app.include_router(scenarios_router)
app.include_router(settings_router)
app.include_router(import_data_router)
app.include_router(dashboard_router)


# --- Health endpoints ---

@app.get("/api/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Liveness probe — app is running."""
    return {"status": "ok"}


@app.get("/api/health/ready", tags=["health"])
async def health_ready() -> dict[str, str]:
    """Readiness probe — checks DB connection and migration status (§13.3).

    Uses a short-lived engine to avoid leaking test-session state.
    """
    from sqlalchemy.ext.asyncio import create_async_engine as _create_engine

    from app.core.config import settings as _settings

    check_engine = _create_engine(_settings.database_url, pool_pre_ping=True)
    try:
        async with check_engine.connect() as conn:
            # Check basic connectivity
            await conn.execute(text("SELECT 1"))

            # Check that Alembic migration version table exists and has a head
            try:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                row = result.first()
                if row is None:
                    return JSONResponse(  # type: ignore[return-value]
                        status_code=503,
                        content={
                            "status": "unavailable",
                            "detail": "Миграции не применены",
                        },
                    )
            except Exception:
                # Table doesn't exist — migrations never ran
                return JSONResponse(  # type: ignore[return-value]
                    status_code=503,
                    content={
                        "status": "unavailable",
                        "detail": "Таблица миграций не найдена",
                    },
                )

        return {"status": "ok"}
    except Exception:
        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content={"status": "unavailable", "detail": "Нет подключения к БД"},
        )
    finally:
        await check_engine.dispose()
