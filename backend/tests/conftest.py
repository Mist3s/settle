"""Root conftest — async test fixtures for integration tests.

Uses the real PostgreSQL database (from Docker Compose).
Each test function gets its own session + savepoint that is rolled back at the end.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database import get_session
from app.main import app


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional DB session that rolls back after each test.

    Creates its own engine per test to avoid event-loop issues.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient wired to the FastAPI app with overridden DB session."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
