# Состояние проекта Settle

**Последнее обновление:** 2026-04-29

## Текущий этап

**Этап 7: Прогноз и дашборд (бэкенд)** — не начат.

## Что известно

- Репозиторий содержит `architecture.md` (v1.0, утверждена), `AGENTS.md`.
- План: 14 этапов, все ADR (001–006) приняты.
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
- **REST API:** /api/loans, /api/payments/{planned,actual}, /api/incomes, /api/scenarios (+actions), /api/settings, /api/import/*, /api/export/*.
- **Audit log:** model_to_dict (column-only, no lazy-load), record() для каждой мутации.
- **Расчётный движок:**
  - `schedule_service.py`: generate_schedule (аннуитет), recalculate_after_prepayment (обе стратегии), solve_for_n.
  - `balance_service.py`: get_latest, create_snapshot, calculate_new_principal.
  - `payment_service.py`: register_payment (полная цепочка: тип → actual → баланс → график → planned status → audit).
  - `GET /api/loans/{id}/schedule`, `POST /api/loans/{id}/recalc-schedule`.
  - Float-сканер тест.
- **Импорт и экспорт данных (этап 6, завершён):**
  - Пакет `services/import_/` (8 модулей, ~1170 строк): storage, header_validator, parser, cross_validator, diff, committer (4 модуля), orchestrator.
  - `services/export_service.py` (212 строк): экспорт 6 сущностей в XLSX.
  - `services/template_service.py` (118 строк): генерация XLSX-шаблона (пустой + с примерами).
  - `domain/constants/import_export.py` (82 строки): единый источник имён листов и колонок.
  - `domain/schemas/import_dto.py` (221 строка): 6 DTO с _parse_decimal/_parse_bool/_parse_date.
  - `domain/schemas/import_report.py` (92 строки): DryRunReport, EntityDiff, ScheduleDiff.
  - `api/routers/import_data.py` (154 строки): POST /import/excel (dry-run), POST /import/excel/commit, GET /import/template, GET /export/excel.
  - `app/cli.py` (166 строк, argparse): template, import (--dry-run/--commit), export.
  - Идемпотентность по бизнес-ключам: Loan(code), Balance(loan_code+snapshot_date), Schedule(loan_code+due_date), Income(code), ActualPayment(loan_code+payment_date+amount).
  - DryRunStore: in-memory dict с TTL 30 мин, lazy GC.
  - Зависимость: python-multipart для multipart/form-data.
- **Тесты:** 223 tests pass (unit + integration). Ruff clean.

## Следующий шаг

Этап 7: Прогноз и дашборд (бэкенд). Предусловие — этап 5 (завершён).

Что нужно:
- `services/forecast_service.py`: `forecast_balance_by_day()` — прогноз свободных денег по дням.
- `services/dashboard_service.py`: агрегаты для главной (ближайшие платежи, остаток на жизнь, общий долг, предупреждения).
- Роутер `api/routers/dashboard.py`: `GET /api/dashboard`, `GET /api/forecast/balance-by-day`.
- Фоновые задачи (APScheduler в lifespan): `accrue_interest` (ежедневно 03:00 МСК), `refresh_planned_status` (ежедневно 00:30 МСК).
- Добавление `overdue` в enum `payment_status` (миграция).
