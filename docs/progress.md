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
