# Состояние проекта Settle

**Последнее обновление:** 2026-04-29

## Текущий этап

**Этап 5: Расчётный движок** — завершён.

Следующий — **Этап 6: Импорт и экспорт данных** (зависит от 5).

## Что известно

- Репозиторий содержит `architecture.md` (v1.0, утверждена), `AGENTS.md`.
- План: 14 этапов, все ADR (001–004) приняты.
- Стек: FastAPI + PostgreSQL 16 + React/TypeScript + Docker.
- Один пользователь, монолит, overlay-симулятор.
- Docker Compose (dev) работает: db (PostgreSQL 16), backend (FastAPI + uvicorn), frontend (Vite + React).
- Backend: pydantic-settings, async SQLAlchemy, structlog JSON, Alembic (async env.py), health endpoints.
- Frontend: Vite + React + TS (strict), Tailwind 4, TanStack Query, path alias @/.
- CI: GitHub Actions (lint + test backend, tsc + build frontend).
- **Доменная модель:** 10 ORM-моделей, 12 PG enum-типов, все индексы/constraints из архитектуры.
- **Миграция:** `001_initial_schema` с явным lifecycle PG enum типов.
- **Аутентификация:** JWT RS256 (access 15 мин, refresh 30 дней), argon2id, seed user.
- **Репозитории:** Generic Repository[Model] с soft-delete auto-filtering, refresh после каждого flush.
- **Сервисы:** loan_service, income_service, payment_service, scenario_service, settings_service, audit_service.
- **Pydantic-схемы:** all entities, `extra='forbid'`, Decimal as string.
- **REST API:** /api/loans, /api/payments/{planned,actual}, /api/incomes, /api/scenarios (+actions), /api/settings.
- **Audit log:** model_to_dict (column-only, no lazy-load), record() для каждой мутации.
- **Расчётный движок:**
  - `schedule_service.py`: generate_schedule (аннуитет), recalculate_after_prepayment (обе стратегии), solve_for_n.
  - `balance_service.py`: get_latest, create_snapshot, calculate_new_principal.
  - `payment_service.py`: register_payment (полная цепочка: тип → actual → баланс → график → planned status → audit).
  - `GET /api/loans/{id}/schedule`, `POST /api/loans/{id}/recalc-schedule`.
  - Float-сканер тест.
- **Тесты:** 92 tests pass (unit + integration). Ruff clean.

## Следующий шаг

Начать этап 6 (импорт и экспорт данных).
