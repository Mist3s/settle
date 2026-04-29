# Состояние проекта Settle

**Последнее обновление:** 2026-04-29

## Текущий этап

**Этап 12: Фронтенд — симулятор, аналитика, настройки** — завершён.

**Следующий:** Этап 13 — E2E-тестирование, production polish.

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
- **Сервисы:** loan_service, income_service, payment_service, scenario_service, settings_service, audit_service, forecast_service, dashboard_service, simulation (package).
- **Pydantic-схемы:** all entities, `extra='forbid'`, Decimal as string.
- **REST API:** /api/loans, /api/payments/{planned,actual}, /api/incomes, /api/scenarios (+actions, +forecast, +apply, +archive), /api/settings, /api/import/*, /api/export/*, /api/dashboard, /api/forecast/balance-by-day.
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
- **Прогноз и дашборд (этап 7, завершён):**
  - `services/forecast_service.py` (107 строк): forecast_balance_by_day — прогноз свободных денег по дням, уважает unavailable_balance.
  - `services/dashboard_service.py` (298 строк): get_dashboard — 4 виджета (next_payments, current_period, totals, warnings).
  - `api/routers/dashboard.py` (66 строк): GET /api/dashboard, GET /api/forecast/balance-by-day.
  - `tasks/scheduler.py` (66 строк): APScheduler AsyncIOScheduler в lifespan, 2 cron job.
  - `tasks/jobs/accrue_interest.py` (87 строк): ежедневное начисление процентов (credit-type, rate>0).
  - `tasks/jobs/refresh_status.py` (46 строк): pending → overdue для просроченных.
  - Миграция не потребовалась — overdue уже в PG enum с миграции 001.
- **Симулятор overlay (этап 8, завершён):**
  - Пакет `services/simulation/` (5 модулей, ~750 строк): projected_state, actions, engine, materializer, __init__.
  - `domain/schemas/simulation.py` (~145 строк): params validators для 6 типов действий, ScenarioForecastResponse (as-is/to-be/diff).
  - 6 типов действий: close_early_full, prepayment_partial, reduce_payment, skip, add_income, change_payment_date.
  - Overlay в памяти: ProjectedState (dataclass), deep-copy для side-by-side сравнения.
  - Engine: загрузка DB → ProjectedState, применение действий, ежедневный прогноз баланса, вычисление diff.
  - Materializer: apply_scenario (материализация в одной транзакции), archive_scenario.
  - 3 новых эндпоинта: GET /{id}/forecast, POST /{id}/apply, POST /{id}/archive.
  - Критический тест: overlay НЕ модифицирует БД (snapshot до/после).
- **Фронтенд каркас (этап 9, завершён):**
  - shadcn/ui (base-nova style) + Settle brand palette (oklch hue 260, light/dark mode).
  - Axios client с JWT refresh interceptor (mutex pattern, queued retry).
  - Zustand: auth store (login/logout/checkAuth), UI store (sidebar).
  - React Router v7: защищённые маршруты (ProtectedRoute), redirect на /login.
  - Layout: Sidebar (desktop ≥1024px), MobileNav (bottom tabs <1024px), Header (sticky).
  - Login page: react-hook-form + zod, Settle branding, error display.
  - API-модули: loans, payments, dashboard, scenarios, settings, import-export.
  - TypeScript types (src/types/api.ts) — зеркало всех Pydantic-схем бэкенда.
  - UI-компоненты (shadcn): button, card, input, label, separator, skeleton, sonner.
  - Vite proxy: /api → backend:8000 (dev mode).
  - Hooks: useMediaQuery.
  - Проверки: tsc --noEmit clean, ESLint clean, production build passes.
- **Фронтенд дашборд и кредиты (этап 10, завершён):**
  - `src/lib/format.ts` — единые утилиты форматирования (money, date, percent, delta, labels).
  - 7 дополнительных shadcn/ui компонентов: badge, dialog, select, table, tabs, tooltip, progress.
  - `LoadingState` — skeleton/error/empty wrapper для useQuery.
  - Дашборд: 4 виджета (NextPayments с urgency color, CurrentPeriod с traffic-light, Totals с delta, Warnings feed) + ForecastChart (Recharts AreaChart).
  - Кредиты: LoanCard (clickable), LoanFilters (type/status/search), LoanFormDialog (create/edit, react-hook-form+zod), ScheduleChart (stacked bar тело/проценты), BalanceFormDialog, StrategyToggle.
  - LoanDetailPage (/loans/:id): полная карточка, график погашения, таблица платежей (table на desktop, cards на mobile).
  - Hooks: useDashboard, useForecast, useLoans, useLoan, useLoanSchedule, CRUD mutations с invalidation.
  - Responsive grid: 1→2→3 колонки (дашборд), 1→2→3 (список кредитов).
  - Проверки: tsc clean, ESLint 0 errors, production build passes.
- **Фронтенд платежи, поступления, календарь (этап 11, завершён):**
  - `api/incomes.ts` (47 строк): CRUD + receive API-модуль.
  - `features/incomes/` (4 файла, ~540 строк): hooks, income-card, income-form (react-hook-form+zod), income-filters.
  - `pages/incomes.tsx` (91 строка): страница поступлений с фильтрацией и CRUD.
  - `features/payments/` (4 файла, ~700 строк): hooks, register-payment-dialog (auto-type detection), payment-card, payment-filters.
  - `features/calendar/` (5 файлов, ~560 строк): hooks, calendar-header, calendar-grid (desktop grid + mobile list), day-cell (цветовая кодировка по loan_type), day-detail.
  - `pages/calendar.tsx` (92 строки): месячный вид с навигацией, интеграция RegisterPaymentDialog.
  - `pages/history.tsx` (79 строк): лента фактических платежей с фильтрами.
  - Навигация: добавлены «Поступления», «История» в sidebar и mobile nav.
  - Route: `/incomes`, `/history`.
  - Интеграция: кнопка «Зарегистрировать платёж» на loan-detail с pre-filled loan_id.
  - Проверки: tsc clean, ESLint 0 errors (3 warnings — known react-hook-form), production build passes (1162 KB JS, 65 KB CSS).
- **Тесты:** 283 tests pass (unit + integration). Ruff clean.

## Следующий шаг

Этап 12: Фронтенд — симулятор, аналитика, настройки.
