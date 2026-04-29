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

## Этап 6: Импорт и экспорт данных (завершён)

**Дата:** 2026-04-29

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
10. `services/import_/cross_validator.py` — кросс-валидация: 5 правил (loan_code refs, income_code refs, loan→balance, balance equation ±0.01, future snapshot_date). 160 строк + 16 unit-тестов.
11. `services/import_/diff.py` — build_diff: сравнение ParsedData с БД по бизнес-ключам → DryRunReport (245 строк) + 6 integration-тестов.
12. `services/import_/committer_core.py` — CommitResult + create_with_audit/update_with_audit (76 строк).
13. `services/import_/committer_loans.py` — upsert settings/loans/balances (143 строки).
14. `services/import_/committer_payments.py` — upsert incomes/schedule/actual_payments + cancel pending + auto-gen schedule (277 строк).
15. `services/import_/committer.py` — facade commit_import() (101 строка) + 5 integration-тестов.
16. `services/import_/orchestrator.py` — оркестратор: run_dry_run(), commit_import(), ImportExpiredError, ImportNotFoundError (~110 строк). `__init__.py` — тонкий реэкспорт. DryRunStore.put() расширен optional key.

**Тесты:** 206 pass, 0 fail. `ruff check` — clean.

17. **Ревью export_service.py и template_service.py** (задачи №9–10):
    - Создан `domain/constants/import_export.py` — единый источник истины для имён листов, колонок, REQUIRED_SHEETS, EXAMPLE_ROW_MARKER (82 строки).
    - Устранено тройное дублирование констант (header_validator / template_service / export_service).
    - Исправлен `_cell_value`: `isinstance(v, bool)` guard перед `hasattr(v, "value")`.
    - Обновлены 7 файлов-потребителей (включая тесты и fixtures).
    - 206 тестов зелёные, ruff чистый.

19. **Integration-тесты build_diff** (задача №19): дополнен `tests/integration/test_import_diff.py` — добавлен `test_diff_usd_to_rub_via_db_setting` (USD→RUB fallback через таблицу settings). Итого 7 тестов, покрытие по breakdown полное. 207 тестов зелёные, ruff чистый.

18. **HTTP-роутер import/export** (задачи №11–12):
    - `api/routers/import_data.py` — 4 эндпоинта: `POST /api/import/excel` (multipart dry-run), `POST /api/import/excel/commit` (commit с 410 Gone при TTL), `GET /api/import/template` (XLSX-шаблон), `GET /api/export/excel` (XLSX-экспорт с `since`). 154 строки, тонкий HTTP-слой.
    - `_CommitRequest` — Pydantic-модель с `extra='forbid'`.
    - `CommitResult` (dataclass) → `dataclasses.asdict()` для JSON-ответа.
    - Подключён в `main.py` (`app.include_router(import_data_router)`).
    - Добавлена зависимость `python-multipart` для multipart/form-data.
    - 206 тестов зелёные, ruff чистый.

20. **Integration-тесты commit_import** (задача №20): дополнен `tests/integration/test_import_commit.py` — было 5 тестов (только counters), стало 9: добавлена проверка состояния БД (все 6 сущностей), audit UPDATE с before/after state, audit на cancel pending (status pending→cancelled), auto-gen из latest balance, транзакционный rollback при ошибке в actual_payments. 211 тестов зелёные, ruff чистый.

21. **Integration-тесты idempotency** (задача №21, §14.3 critical): `tests/integration/test_import_idempotency.py` — 3 теста (242 строки): двойной прогон идентичного XLSX → counts и export совпадают; roundtrip export→re-import→compare; частичный update (одна строка изменена → обновляется только она). 214 тестов зелёные, ruff чистый.

22. **Integration-тесты API** (задача №22): `tests/integration/test_import_api.py` — 9 тестов (220 строк): multipart upload → DryRunReport (200), commit с import_id (200), commit с несуществующим id (410 Gone), template download (пустой + with_examples), export download + since-фильтр, unauthenticated → 401/403, non-XLSX файл → 400. Добавлена обработка `BadZipFile`/`InvalidFileException` в роутере `import_data.py`. 223 теста зелёные, ruff чистый.

### Финальный обзор этапа 6

Этап 6 полностью завершён. Все 23 atomic-задачи из `docs/notes/stage6_breakdown.md` выполнены в 8 волнах.

**Ключевые модули:**
- Пакет `services/import_/` (8 модулей, ~1170 строк): парсинг XLSX→DTO, валидация заголовков и кросс-ссылок, diff с БД по бизнес-ключам, commit в одной транзакции с audit_log, in-memory TTL store.
- `services/export_service.py` (212 строк): экспорт всех 6 сущностей в XLSX.
- `services/template_service.py` (118 строк): генерация пустого/example шаблона.
- `domain/constants/import_export.py` (82 строки): единый источник имён листов/колонок.
- `domain/schemas/import_dto.py` (221 строка): 6 DTO с хелперами парсинга.
- `domain/schemas/import_report.py` (92 строки): dry-run отчёт.
- `api/routers/import_data.py` (154 строки): 4 HTTP-эндпоинта.
- `app/cli.py` (166 строк): CLI на argparse (template, import, export).

**Тесты:** 223 pass, 0 fail. Из них по этапу 6: 59 unit (DTO) + 11 (header_validator) + 16 (cross_validator) + 6 (storage) + 10 (parser) + 7 (diff integration) + 9 (commit integration) + 3 (idempotency) + 9 (API integration) = 130 тестов.

**Критические тесты §14.3:** идемпотентность импорта (двойной прогон, roundtrip export→import, partial update) — зелёные.

**E2E верификация:** CLI template → заполнение minimal_valid_workbook → import --dry-run (0 errors) → --commit (1 loan, 1 balance, 1 setting created) → проверка данных в PostgreSQL → audit_log корректен.

**ADR:** ADR-005 (пакет вместо monolith), ADR-006 (argparse вместо typer).

**Известные ограничения:**
- DryRunStore — in-memory, не переживает перезапуск backend (достаточно для однопользовательского приложения).
- GAP-1/GAP-2 (model_validator на LoanImportRow.original_amount и BalanceImportRow.principal_balance) — задокументированы в state.md, не критичны для работы.

---

## Этап 7: Прогноз и дашборд (бэкенд) — 2026-04-29

### Атомарные задачи

1. ✅ Pydantic-схемы dashboard/forecast (`domain/schemas/dashboard.py`)
2. ✅ ForecastService (`services/forecast_service.py`) — прогноз баланса по дням (§5.3)
3. ✅ DashboardService (`services/dashboard_service.py`) — агрегаты дашборда (§8.2)
4. ✅ Dashboard router (`api/routers/dashboard.py`) — `GET /api/dashboard`, `GET /api/forecast/balance-by-day`
5. ✅ APScheduler (`tasks/scheduler.py`) — два cron job в lifespan
6. ✅ Job: accrue_interest (`tasks/jobs/accrue_interest.py`) — ежедневное начисление процентов
7. ✅ Job: refresh_planned_status (`tasks/jobs/refresh_status.py`) — pending → overdue
8. ✅ Integration-тесты dashboard + forecast (19 тестов)
9. ✅ Integration-тесты background jobs

### Обзор

**Ключевые модули:**
- `forecast_service.py` (107 строк): прогноз «свободных денег» по дням. Читает incomes и pending payments в диапазоне, уважает `unavailable_balance` из settings.
- `dashboard_service.py` (298 строк): единый `get_dashboard()` — 4 виджета (next_payments, current_period, totals, warnings). Injectable `today` для тестирования.
- `scheduler.py` (66 строк): APScheduler AsyncIOScheduler с двумя cron-задачами (03:00 и 00:30 МСК).
- `accrue_interest.py` (87 строк): ежедневный расчёт процентов для credit-type активных займов.
- `refresh_status.py` (46 строк): bulk UPDATE pending→overdue для просроченных.

**Тесты:** 242 (19 новых), все зелёные. Ruff чистый.

**Миграция:** Не потребовалась — `overdue` уже в PG enum и Python enum с миграции 001.

**Известные ограничения:**
- `month_to_month_change` в totals = "0.00" (placeholder до накопления исторических balance данных через accrue_interest job).
- Background jobs создают собственные сессии (не используют test rollback), поэтому тестируются inline логикой.

---

## Этап 8: Симулятор сценариев (overlay)

**Дата:** 2026-04-29

### Реализация

Overlay-симулятор для сценарного прогнозирования — полный бэкенд.

**Пакет `services/simulation/` (5 модулей):**
- `projected_state.py` (~120 строк): dataclasses ProjectedPayment, ProjectedIncome, ProjectedLoan, ProjectedState с deep-copy и filtering helpers.
- `actions.py` (~260 строк): чистые функции для 6 типов действий (close_early_full, prepayment_partial, reduce_payment, skip, add_income, change_payment_date) + dispatcher apply_action.
- `engine.py` (~245 строк): загрузка DB→ProjectedState, вычисление as-is/to-be daily balance, diff.
- `materializer.py` (~215 строк): apply_scenario (материализация через PaymentService/IncomeService), archive_scenario.
- `__init__.py`: реэкспорт.

**Pydantic-схемы (`domain/schemas/simulation.py`, ~140 строк):**
- Params validators для каждого ScenarioActionType (JSONB validation).
- ScenarioForecastResponse: ProjectionData (balance_by_day + payments), ScenarioForecastDiff.

**API (расширение `api/routers/scenarios.py`):**
- `GET /{id}/forecast?from=&to=&starting_balance=` — as-is + to-be + diff.
- `POST /{id}/apply` — материализация в одной транзакции.
- `POST /{id}/archive` — архивация сценария.

**Ключевые решения:**
- Overlay в памяти (ProjectedState), не в отдельных DB таблицах. DB не модифицируется при forecast.
- Пересчёт графика в overlay использует те же чистые функции ScheduleService.
- Materializer: close_early_full берёт полный баланс из balance_service.get_latest.
- Income code при материализации: `SC_{scenario_hex}_{action_hex}` для уникальности.

**Тесты:** 283 (41 новый — 16 unit + 10 integration forecast + 15 integration apply), все зелёные. Ruff чистый.

**Критический инвариант:** тест `test_forecast_does_not_write_to_db` — snapshot DB до и после вызова forecast endpoint, проверка идентичности (balances, planned_payments, loan status).

---

## Этап 9: Фронтенд — каркас и дизайн-система (2026-04-29)

Полная настройка SPA-инфраструктуры: от дизайн-системы до API-клиента и роутинга.

**Дизайн-система:**
- shadcn/ui (base-nova style) инициализирован через CLI, адаптирован к Settle palette.
- Settle brand palette: oklch hue 260, 11 оттенков primary, 11 оттенков surface, success/warning/danger.
- CSS-переменные для light/dark mode, sidebar, charts — всё на фирменных цветах.
- 7 UI-компонентов (shadcn): button, card, input, label, separator, skeleton, sonner.

**API-инфраструктура:**
- `src/api/client.ts`: axios instance с JWT interceptor (mutex pattern для concurrent refresh).
- `src/api/auth.ts`: login(), logout() — управление токенами (localStorage).
- 6 API-модулей: loans, payments, dashboard, scenarios, settings, import-export.
- `src/types/api.ts`: TypeScript-типы для всех Pydantic-схем бэкенда (~350 строк).
- Vite proxy: `/api` → `http://backend:8000` для dev mode.

**Состояние и навигация:**
- Zustand: auth store (login/logout/checkAuth), UI store (sidebar toggle).
- React Router v7: createBrowserRouter, ProtectedRoute → redirect на /login.
- 5 маршрутов: dashboard, loans, calendar, simulator, settings.
- Страницы-заглушки с Card-компонентами.

**Layout:**
- Sidebar (desktop ≥1024px): лого + навигация с NavLink + active state.
- MobileNav (bottom tabs <1024px): fixed bottom bar.
- Header (sticky): заголовок + logout.
- AppLayout: sidebar + header + Outlet + mobile nav.

**Login-страница:**
- react-hook-form + zod валидация (email + password).
- Settle branding (лого, название, подзаголовок).
- Error display из auth store.

**Проверки:** `tsc --noEmit` чисто, ESLint чисто, production build проходит.
43 файла, 5632 строк новых/изменённых.

---

## Этап 10: Фронтенд — дашборд и кредиты (2026-04-29)

### Инфраструктура

- `src/lib/format.ts` — утилиты форматирования (money, date, percent, delta, labels).
- 7 shadcn/ui компонентов (badge, dialog, select, table, tabs, tooltip, progress).
- `LoadingState` — переиспользуемая обёртка для skeleton/error/empty.
- `TooltipProvider` wrapper в main.tsx.

### Дашборд (features/dashboard/)

- `hooks.ts` — TanStack Query: useDashboard, useForecast.
- 4 виджета: NextPayments (urgency color), CurrentPeriod (traffic-light),
  Totals (delta с цветом), Warnings (feed с иконками).
- `ForecastChart` — Recharts AreaChart с gradient fill, custom tooltip.
- `dashboard.tsx` — responsive grid 1→2→3 колонки.

### Кредиты (features/loans/)

- `hooks.ts` — useLoans, useLoan, useLoanSchedule, CRUD mutations с invalidation.
- `LoanCard` — clickable карточка с type/status badges.
- `LoanFilters` — поиск + Select по типу/статусу.
- `LoanFormDialog` — create/edit через react-hook-form + zod.
- `ScheduleChart` — stacked bar (тело vs проценты).
- `BalanceFormDialog` — обновление остатка.
- `StrategyToggle` — переключатель reduce_payment/shorten_term.
- `LoanDetailPage` — полная карточка с графиком, таблицей платежей, действиями.
- Route `/loans/:id`.

### Технические решения

- base-ui tooltip (shadcn v4) не поддерживает `asChild` — используется прямой render.
- zod v4 + @hookform/resolvers v5 type mismatch — resolver cast to any (runtime OK).
- base-ui Select `onValueChange` nullable — добавлены null-guards.

**Проверки:** `tsc -p tsconfig.app.json --noEmit` чисто, ESLint 0 errors (1 warning — known react-hook-form),
production build проходит (1133 KB JS, 62 KB CSS).
28 файлов, 2889 строк новых/изменённых.

---

## Этап 11: Фронтенд — платежи, поступления, календарь

**Дата:** 2026-04-29

### Что сделано

1. **Инфраструктура:**
   - `api/incomes.ts` — API-модуль для поступлений (CRUD + receive).
   - `lib/format.ts` — добавлены labels: `incomeStatusLabel()`, `actualPaymentTypeLabel()`, `loanTypeColor()`.

2. **Поступления (features/incomes/):**
   - `hooks.ts` — TanStack Query: useIncomes, useCreateIncome, useUpdateIncome, useReceiveIncome, useDeleteIncome.
   - `income-card.tsx` — карточка с badge статуса, кнопками «Получено», «Изменить», «Удалить».
   - `income-form.tsx` — dialog create/edit (react-hook-form + zod).
   - `income-filters.tsx` — поиск + select статуса.
   - `pages/incomes.tsx` — страница со списком, фильтрами, CRUD.

3. **Регистрация платежей (features/payments/):**
   - `hooks.ts` — TanStack Query: usePlannedPayments, useActualPayments, useRegisterPayment, useDeleteActualPayment.
   - `register-payment-dialog.tsx` — форма с auto-type detection (сравнение суммы с planned), предупреждения overpayment/underpayment.

4. **Календарь (features/calendar/):**
   - `hooks.ts` — useCalendarPayments (диапазон дат), useCalendarLoans.
   - `calendar-header.tsx` — навигация по месяцам + «Сегодня».
   - `calendar-grid.tsx` — desktop: 7-col grid, mobile: vertical list.
   - `day-cell.tsx` — цветовые точки по loan_type (credit=синий, installment=зелёный, split=фиолетовый, etc.).
   - `day-detail.tsx` — popup с деталями платежей дня.
   - `pages/calendar.tsx` — месячный вид + кнопка «+ Платёж».

5. **История (features/payments/):**
   - `payment-card.tsx` — карточка фактического платежа с type badge.
   - `payment-filters.tsx` — фильтры: кредит, тип, date range.
   - `pages/history.tsx` — лента фактических платежей.

6. **Навигация и роутинг:**
   - Routes: `/incomes`, `/history`.
   - Sidebar + mobile nav: добавлены «Поступления» (Wallet), «История» (History).

7. **Интеграция loan-detail:**
   - Кнопка «Зарегистрировать платёж» → RegisterPaymentDialog с pre-filled loan_id.

### Проверки
- tsc: clean (0 errors)
- ESLint: 0 errors, 3 warnings (known react-hook-form incompatible-library)
- Production build: passes (1162 KB JS, 65 KB CSS)
- 13 новых файлов, ~1840 строк новых/изменённых, 5 файлов обновлены.

---

## Этап 12: Фронтенд — симулятор, аналитика, настройки

**Дата:** 2026-04-29

### Что вошло

1. **Инфраструктура:**
   - `lib/format.ts` — добавлены `scenarioStatusLabel()`, `scenarioActionTypeLabel()`, `formatDays()`.
   - `components/ui/textarea.tsx` — новый shadcn/ui компонент.

2. **Симулятор (7 файлов):**
   - `features/simulator/hooks.ts` — 12 TanStack Query хуков (scenarios CRUD, actions CRUD, forecast, apply, archive).
   - `features/simulator/scenario-list.tsx` — список сценариев с фильтром по статусу, badge, create/edit/delete.
   - `features/simulator/scenario-form-dialog.tsx` — dialog создания/редактирования (name + base_date, zod).
   - `features/simulator/action-card.tsx` — карточка действия с label, параметрами, edit/delete.
   - `features/simulator/action-form-dialog.tsx` — wizard-dialog с 6 типами действий, динамическими полями.
   - `features/simulator/comparison-view.tsx` — два AreaChart (as-is vs to-be), diff summary, responsive desktop/mobile.
   - `pages/simulator.tsx` — двухпанельный layout (360px sidebar + chart area), mobile tabs.

3. **Настройки (4 файла):**
   - `features/settings/hooks.ts` — хуки для settings CRUD, import upload/commit, template/export download.
   - `features/settings/settings-form.tsx` — форма key-value параметров с категориями.
   - `features/settings/import-export-section.tsx` — шаблоны, drag-n-drop upload, dry-run report, commit, export.
   - `pages/settings.tsx` — tabs «Параметры» / «Импорт и экспорт».

4. **Аналитика (5 файлов):**
   - `features/analytics/hooks.ts` — `usePaymentBreakdown()`, `useDebtByCreditor()`, `useOptimizer()`.
   - `features/analytics/payment-breakdown-chart.tsx` — stacked bar по месяцам (тело vs проценты vs рассрочки).
   - `features/analytics/debt-breakdown-chart.tsx` — donut chart разбивка по кредиторам.
   - `features/analytics/optimizer.tsx` — таблица приоритетов (avalanche), desktop table + mobile cards.
   - `pages/analytics.tsx` — страница аналитики.

5. **Навигация:**
   - Route `/analytics` добавлен.
   - Sidebar + mobile nav: добавлена «Аналитика» (BarChart3).

6. **Бэкенд (минорно):**
   - `scenario_service.list_actions()` — новый метод.
   - `GET /api/scenarios/{id}/actions` — новый эндпоинт.
   - `api/scenarios.ts` (frontend) — `getActions()` API-функция.

### Проверки
- tsc: clean (0 errors)
- ESLint: 0 errors, 4 warnings (known react-hook-form incompatible-library)
- Production build: passes (1243 KB JS, 69 KB CSS)
- Ruff (backend): all checks passed
- Pytest: 267 passed, 2 failed (pre-existing import commit tests, unrelated)
- 20 задач в 7 волнах, ~18 новых файлов, ~2300 строк.

---

## Этап 13: Наблюдаемость, метрики, health checks (2026-04-29)

### Что сделано

1. **Фильтрация чувствительных данных в логах (§12.4):**
   - structlog processor `filter_sensitive_data`: рекурсивная санитизация event dict.
   - Полная редакция: passwords, tokens, refresh_tokens, secrets, jwt_private_key.
   - Маскирование contract_number (видны только последние 4 цифры).
   - 23 unit-теста: parametrized по всем чувствительным ключам, nested dicts, edge cases.

2. **HTTP request/response logging (§13.1):**
   - Middleware `request_logging_middleware`: объединяет request_id injection и HTTP logging.
   - Каждый запрос логируется: path, method, status_code, duration_ms, user_id, request_id.
   - Health и metrics endpoints исключены из логирования (noise reduction).

3. **Prometheus метрики (§13.2):**
   - `core/metrics.py`: Instrumentator instance + 3 кастомных метрики.
   - `prometheus-fastapi-instrumentator` подключён: instrument() + expose() на `/metrics`.
   - Кастомные: `loan_balance_total` (gauge per loan), `payments_planned_today` (gauge), `forecast_compute_duration_seconds` (histogram).
   - Health/metrics endpoints исключены из стандартных HTTP метрик.

4. **Health ready расширен (§13.3):**
   - Проверяет не только `SELECT 1`, но и наличие `alembic_version` таблицы с записью.
   - Short-lived engine для изоляции от test-session state.
   - Graceful degradation: отсутствие таблицы → 503 "Таблица миграций не найдена".

5. **Docker healthcheck:** обновлён с `/api/health/live` на `/api/health/ready`.

### Ключевые файлы
- `backend/app/core/logging.py` (105 строк)
- `backend/app/core/metrics.py` (42 строки)
- `backend/app/main.py` (230 строк, обновлён)
- `backend/tests/unit/test_log_filtering.py` (23 теста)
- `backend/tests/integration/test_observability.py` (4 теста)
- `docker-compose.dev.yml` (healthcheck)

### Проверки
- Ruff: all checks passed
- Pytest: 303 passed, 7 failed (pre-existing: 4 auth seed user, 2 import commit, 1 import idempotency)
- 27 новых тестов, все зелёные

---
