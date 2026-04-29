# Состояние проекта Settle

**Последнее обновление:** 2026-04-29

## Текущий этап

**Этап 1: Каркас проекта и инфраструктура** — завершён.

Следующий — **Этап 2: Доменная модель и миграции** (зависит от 1)
и **Этап 3: Аутентификация и безопасность** (зависит от 1).
Этапы 2 и 3 могут выполняться параллельно.

## Что известно

- Репозиторий содержит `architecture.md` (v1.0, утверждена), `AGENTS.md`.
- План: 14 этапов, все ADR (001–004) приняты.
- Стек: FastAPI + PostgreSQL 16 + React/TypeScript + Docker.
- Один пользователь, монолит, overlay-симулятор.
- Docker Compose (dev) работает: db (PostgreSQL 16), backend (FastAPI + uvicorn), frontend (Vite + React).
- Backend: pydantic-settings, async SQLAlchemy, structlog JSON, Alembic (async env.py), health endpoints.
- Frontend: Vite + React + TS (strict), Tailwind 4, TanStack Query, path alias @/.
- CI: GitHub Actions (lint + test backend, tsc + build frontend).

## Следующий шаг

Начать этап 2 (доменная модель и миграции) или этап 3 (auth).
