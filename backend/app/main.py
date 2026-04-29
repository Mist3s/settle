"""FastAPI application entrypoint."""

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
from app.api.routers.import_data import router as import_data_router
from app.api.routers.incomes import router as incomes_router
from app.api.routers.loans import router as loans_router
from app.api.routers.payments import router as payments_router
from app.api.routers.scenarios import router as scenarios_router
from app.api.routers.settings import router as settings_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.domain.models.user import User


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


# --- Health endpoints ---

@app.get("/api/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Liveness probe — app is running."""
    return {"status": "ok"}


@app.get("/api/health/ready", tags=["health"])
async def health_ready() -> dict[str, str]:
    """Readiness probe — checks DB connection."""
    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content={"status": "unavailable", "detail": "Нет подключения к БД"},
        )
