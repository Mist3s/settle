# Состояние проекта Settle

**Последнее обновление:** 2026-04-29

## Текущий этап

**Этап 2: Доменная модель и миграции** — завершён.
**Этап 3: Аутентификация и безопасность** — завершён.

Следующий — **Этап 4: Репозитории и базовый CRUD** (зависит от 2 и 3).

## Что известно

- Репозиторий содержит `architecture.md` (v1.0, утверждена), `AGENTS.md`.
- План: 14 этапов, все ADR (001–004) приняты.
- Стек: FastAPI + PostgreSQL 16 + React/TypeScript + Docker.
- Один пользователь, монолит, overlay-симулятор.
- Docker Compose (dev) работает: db (PostgreSQL 16), backend (FastAPI + uvicorn), frontend (Vite + React).
- Backend: pydantic-settings, async SQLAlchemy, structlog JSON, Alembic (async env.py), health endpoints.
- Frontend: Vite + React + TS (strict), Tailwind 4, TanStack Query, path alias @/.
- CI: GitHub Actions (lint + test backend, tsc + build frontend).
- **Доменная модель:** 10 ORM-моделей (users, loans, loan_balances, incomes, planned_payments, actual_payments, scenarios, scenario_actions, settings, audit_log), 12 PG enum-типов, все индексы/constraints из архитектуры.
- **Миграция:** `001_initial_schema` с явным lifecycle PG enum типов. upgrade/downgrade/upgrade проходят чисто.
- **Аутентификация:** JWT RS256 (access 15 мин, refresh 30 дней), argon2id хеширование, seed user из .env, RFC 7807 error format, `extra='forbid'` на request-схемах.
- **Health ready:** проверяет подключение к БД (SELECT 1).

## Следующий шаг

Начать этап 4 (репозитории и CRUD).
