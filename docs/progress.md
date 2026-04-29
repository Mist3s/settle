# Журнал прогресса — Settle

Записи добавляются в конце каждого завершённого этапа.

---

## Этап 1: Каркас проекта и инфраструктура (2026-04-29)

**Что сделано:**

- Backend: `pyproject.toml` (FastAPI, SQLAlchemy async, Alembic, structlog, JWT, argon2, openpyxl, APScheduler, Prometheus), пакетная структура по архитектуре (core/, domain/, repositories/, services/, api/, tasks/, tests/).
- `core/config.py` — pydantic-settings (DB, JWT RS256, seed user, CORS, logging).
- `core/database.py` — async engine + session factory (expire_on_commit=False).
- `core/logging.py` — structlog JSON с contextvars (request_id).
- `main.py` — FastAPI с lifespan, CORS middleware, request_id middleware, health endpoints (`/api/health/live`, `/api/health/ready`).
- Alembic init: async `env.py`, migration template, versions dir.
- `Dockerfile` (dev, hot-reload).
- Frontend: Vite + React + TypeScript (strict), Tailwind 4 (`@tailwindcss/vite`), Inter font, OKLCH palette, path alias @/.
- TanStack Query (staleTime 30s, gcTime 5min), react-router-dom, zustand, recharts, date-fns, sonner, zod, react-hook-form, axios.
- `docker-compose.dev.yml`: PostgreSQL 16 + backend + frontend, health checks.
- `.env.example`, `Makefile` (up/down/logs/lint/test/migrate/keys), `.gitignore`.
- GitHub Actions CI: backend lint (ruff) + test (pytest w/ PG service), frontend tsc + build.

**Ключевые файлы:** `backend/app/main.py`, `backend/app/core/`, `backend/pyproject.toml`, `frontend/src/`, `docker-compose.dev.yml`, `.github/workflows/ci.yml`.

**Верификация:**
- `docker compose up` — все 3 контейнера стартуют, db + backend healthy.
- `GET /api/health/live` → `{"status":"ok"}` (200).
- `http://localhost:5173` → React SPA с Settle branding (200).

**Ограничения:** Docs endpoints (`/api/docs`) доступны только при `DEBUG=true`. Readiness check (`/api/health/ready`) пока не проверяет БД (будет в этапе 2).

---

## Этап 2: Доменная модель и миграции (2026-04-29)

**Что сделано:**

- `domain/enums.py` — 12 Python enum-классов (str, Enum), зеркалящие PG enum types.
- `domain/models/base.py` — DeclarativeBase с naming convention, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin.
- `domain/models/pg_enums.py` — централизованные PG ENUM определения с `values_callable` для lowercase значений.
- ORM-модели: `user.py`, `loan.py`, `balance.py`, `payment.py` (PlannedPayment + ActualPayment), `income.py`, `scenario.py` (Scenario + ScenarioAction), `settings.py`, `audit.py`.
- `domain/models/__init__.py` — реэкспорт всех моделей.
- `alembic/env.py` — `target_metadata = Base.metadata`.
- Миграция `001_initial_schema` — явное создание/удаление PG enum типов, все таблицы, индексы, CHECK/UNIQUE constraints.
- Верификация: `upgrade head` → `downgrade base` → `upgrade head` — всё чисто.

**Ключевые файлы:** `backend/app/domain/enums.py`, `backend/app/domain/models/`, `backend/alembic/versions/3c0c449dc472_001_initial_schema.py`.

**Тесты:** Миграция upgrade/downgrade работает. Constraints (interest_rate >= 0, closing_date >= opening_date, unique loans.code) действуют.

---

## Этап 3: Аутентификация и безопасность (2026-04-29)

**Что сделано:**

- `core/security.py` — JWT RS256 (python-jose), argon2id (argon2-cffi). Ключи из filesystem.
- `domain/schemas/auth.py` — LoginRequest, TokenResponse, RefreshRequest с `extra='forbid'`.
- `api/routers/auth.py` — `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`.
- `api/deps.py` — `get_current_user` dependency (HTTPBearer + JWT validation + user lookup).
- Seed user в lifespan (`_seed_user()`, идемпотентный — проверяет email).
- RFC 7807 error format для `RequestValidationError`.
- `make keys` — генерация JWT RS256 ключей.
- `/api/health/ready` теперь проверяет подключение к БД (SELECT 1).

**Ключевые файлы:** `backend/app/core/security.py`, `backend/app/api/routers/auth.py`, `backend/app/api/deps.py`, `backend/app/main.py`.

**Верификация:**
- Login: `POST /api/auth/login` → 200 с access + refresh tokens.
- Неверный пароль → 401 `"Неверный email или пароль"`.
- Extra field → 422 RFC 7807 `"extra_forbidden"`.
- Refresh: `POST /api/auth/refresh` → 200 с новой парой токенов.
- Seed user: при старте backend проверяет и создаёт пользователя из .env.

**Ограничения:** Logout — no-op (stateless JWT, нет blocklist). Future: Redis token blocklist.

