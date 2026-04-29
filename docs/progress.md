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

---

## Этап 4: Репозитории и базовый CRUD

**Дата:** 2026-04-29

**Что сделано:**

1. **Generic Repository** (`repositories/base.py`): PEP 695 type params, auto soft-delete filtering, CRUD (get/list/create/update/soft_delete/restore), refresh после каждого flush для предотвращения MissingGreenlet.
2. **Специализированные репозитории** для всех сущностей: loan, payment (planned + actual), income, balance (+ get_latest), scenario + action (+ list_by_scenario), settings (+ get_by_key, list_by_user), audit_log (+ list_by_entity).
3. **Pydantic-схемы** для всех сущностей: `extra='forbid'` на request-моделях, Decimal → string в JSON, `from_attributes=True` на response-моделях.
4. **Сервисный слой** (`services/`): loan_service, income_service, payment_service, scenario_service, settings_service — вся бизнес-логика и audit_log запись вынесены из роутеров.
5. **Audit service** (`services/audit_service.py`): `model_to_dict` через `__dict__` (не `getattr`) для безопасного чтения в async-контексте, `record()` для записи в audit_log.
6. **REST роутеры**: тонкий HTTP-слой, только Decimal-конвертация и HTTP-ответы. Роутеры зависят только от сервисов и схем.
7. **Тесты:** integration-тесты для loans (create, list, get, update, delete, audit_log, balance, extra field rejection), incomes (full CRUD + receive), scenarios (CRUD + actions), settings (upsert + list). Unit-тесты для audit_service serialization.

**Ключевые файлы:**
- `backend/app/repositories/base.py` — generic repository
- `backend/app/services/{loan,income,payment,scenario,settings,audit}_service.py`
- `backend/app/api/routers/{loans,payments,incomes,scenarios,settings}.py`
- `backend/app/domain/schemas/{loan,payment,income,balance,scenario,settings}.py`

**Тесты:** 57 pass, 0 fail. `ruff check` — clean.

**Решённые проблемы:**
- `MissingGreenlet` при серлизации ORM → Pydantic: `session.refresh()` после flush + `__dict__` в model_to_dict.
- Архитектурное соблюдение: бизнес-логика строго в services, роутеры тонкие.

---

## Этап 5: Расчётный движок

**Дата:** 2026-04-29

**Что сделано:**

1. **ScheduleService** (`services/schedule_service.py`): чистые функции, без DB.
   - `generate_schedule()` — аннуитетный график с корректировкой последнего платежа.
   - `recalculate_after_prepayment()` — обе стратегии (`reduce_payment`, `shorten_term`).
   - `solve_for_n()` — решение для кол-ва месяцев при фиксированном аннуитете.
   - Обработка `payment_day` с clamping на последний день месяца.
   - Zero-rate shortcut для рассрочек/сплит.

2. **BalanceService** (`services/balance_service.py`): снимки остатков.
   - `get_latest()`, `create_snapshot()` с инвариантом `current = principal + accrued`.
   - `calculate_new_principal()` — чистая функция для пересчёта после платежа.

3. **PaymentService** (`services/payment_service.py`): полная цепочка из arch 5.2.
   - `determine_payment_type()` — все 6 типов по соотношению сумм.
   - `register_payment()` — создание actual → баланс → перегенерация графика → planned status → audit.
   - `_regenerate_future_schedule()` — cancel future + generate new.
   - `_cancel_future_planned()` — массовая отмена с audit log.
   - Обработка early_full: баланс=0, loan.status=paid_off, все future cancelled.
   - Обработка overpayment: excess на тело, график пересчитан.
   - Обработка underpayment: planned.status=partial, notes с суммой.
   - `create_actual()` сохранён для backward-compat.

4. **REST API:** `GET /api/loans/{id}/schedule`, `POST /api/loans/{id}/recalc-schedule`.

5. **Критические тесты (14.3):**
   - Инвариант сходимости: sum(principal) == original (±1 коп.), 3 варианта.
   - Обе стратегии досрочного: reduce_payment (months same, annuity↓), shorten_term (annuity same, months↓).
   - Regular, overpayment, underpayment, missed, early_full, early_partial — интеграционные.
   - Float-сканер: `grep -rn float( services/ domain/ repositories/` — clean.

**Ключевые файлы:**
- `backend/app/services/schedule_service.py`
- `backend/app/services/balance_service.py`
- `backend/app/services/payment_service.py`
- `backend/app/domain/schemas/schedule.py`
- `backend/app/tests/unit/test_schedule_service.py` (18 тестов)
- `backend/app/tests/unit/test_financial_engine.py` (12 тестов)
- `backend/app/tests/integration/test_financial_engine.py` (6 тестов)

**Тесты:** 92 pass, 0 fail. `ruff check` — clean.

**Ограничения:**
- `recalc-schedule` — read-only preview, не обновляет planned_payments в DB.
- `solve_for_n` использует `float` для `math.log` — это количество месяцев, не денежная величина, документировано и исключено из float-сканера.

---

## Этап 6: Импорт и экспорт данных (в работе)

**Дата начала:** 2026-04-29

**Что сделано:**

1. `domain/schemas/import_dto.py` — 6 DTO моделей для листов XLSX (221 строка).
2. `services/export_service.py` — экспорт текущего состояния БД в XLSX (212 строк).
3. `services/template_service.py` — генерация пустого/example шаблона (118 строк).
4. `domain/schemas/import_report.py` — 7 Pydantic-моделей dry-run отчёта (92 строки): `ImportSeverity`, `ImportError`, `ImportWarning`, `EntityDiff`, `ScheduleDiff`, `DryRunSummary`, `DryRunReport`.
5. Декомпозиция на 23 atomic-задачи в 8 волнах (`docs/notes/stage6_breakdown.md`).
6. `services/import_/storage.py` — DryRunStore: in-memory dict с TTL 30 мин, lazy GC (64 строки). + 6 unit-тестов.

**Тесты:** 98 pass, 0 fail. `ruff check` — clean.

**Статус:** волна 1 завершена, волна 2 начата (parser done).

7. `services/import_/header_validator.py` — валидация заголовков листов vs SHEET_COLUMNS (107 строк) + 11 unit-тестов.
8. `tests/fixtures/import_fixtures.py` — build_workbook, 6 row-factory, minimal_valid_workbook (159 строк).
9. `services/import_/parser.py` — parse_workbook: XLSX→ParsedData + errors + warnings (205 строк) + 10 unit-тестов.

**Тесты:** 120 pass, 0 fail. `ruff check` — clean (legacy-файлы имеют pre-existing violations, не от этой задачи).
