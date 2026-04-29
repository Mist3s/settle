# Декомпозиция Этапа 7: Прогноз и дашборд (бэкенд)

**Дата:** 2026-04-29

## Предусловия

- `overdue` уже в PG enum `payment_status` и Python `PaymentStatus` — миграция НЕ нужна.
- Все сервисы (schedule, balance, payment, income, settings, loan) готовы.
- 223 теста зелёные, ruff чистый.

## Оценка объёма

| Компонент | Ожидаемый размер | Файлов |
|-----------|-----------------|--------|
| Pydantic-схемы (dashboard, forecast) | ~80 строк | 1 |
| forecast_service.py | ~150 строк | 1 |
| dashboard_service.py | ~180 строк | 1 |
| dashboard.py (роутер) | ~80 строк | 1 |
| tasks/scheduler.py | ~60 строк | 1 |
| tasks/jobs/accrue_interest.py | ~80 строк | 1 |
| tasks/jobs/refresh_status.py | ~60 строк | 1 |
| Тесты unit + integration | ~350 строк | 3-4 |

**Итого:** ~1040 строк в ~10 файлах. Все файлы <200 строк.

## Atomic-задачи

### Волна 1: Схемы и инфраструктура

| # | Задача | Файл(ы) | Описание |
|---|--------|---------|----------|
| 1 | Pydantic-схемы dashboard/forecast | `domain/schemas/dashboard.py` | `DailyBalance`, `NextPayment`, `CurrentPeriod`, `DashboardTotals`, `DashboardWarning`, `DashboardResponse`, `ForecastResponse` |

### Волна 2: Сервисы

| # | Задача | Файл(ы) | Описание |
|---|--------|---------|----------|
| 2 | ForecastService | `services/forecast_service.py` | `forecast_balance_by_day()` — по §5.3 архитектуры: стартовый баланс, проход по дням, incomes +, payments -, overlay support |
| 3 | Unit-тесты forecast | `tests/unit/test_forecast_service.py` | Чистая логика: нет incomes/payments → flat; один income → step up; один payment → step down; mixed; пустой диапазон |
| 4 | DashboardService | `services/dashboard_service.py` | `get_dashboard()` → агрегат: next_payments (3 ближайших pending), current_period (income vs payments до следующего income), totals (total_debt, active_loans, m2m change), warnings |
| 5 | Integration-тесты dashboard + forecast | `tests/integration/test_dashboard.py` | Создать данные → GET /api/dashboard → verify structure; GET /api/forecast/balance-by-day → verify curve |

### Волна 3: Роутер

| # | Задача | Файл(ы) | Описание |
|---|--------|---------|----------|
| 6 | Dashboard router | `api/routers/dashboard.py` | `GET /api/dashboard`, `GET /api/forecast/balance-by-day` + подключение в main.py |

### Волна 4: Фоновые задачи

| # | Задача | Файл(ы) | Описание |
|---|--------|---------|----------|
| 7 | APScheduler setup | `tasks/__init__.py`, `tasks/scheduler.py` | APScheduler AsyncScheduler в lifespan, timezone Europe/Moscow |
| 8 | Job: accrue_interest | `tasks/jobs/__init__.py`, `tasks/jobs/accrue_interest.py` | Ежедневно 03:00 МСК: для каждого active loan — создать balance snapshot с accrued interest |
| 9 | Job: refresh_planned_status | `tasks/jobs/refresh_status.py` | Ежедневно 00:30 МСК: pending planned_payments с due_date < today → overdue |
| 10 | Unit-тесты jobs | `tests/unit/test_background_jobs.py` | accrue_interest создаёт snapshots; refresh_status переводит в overdue; idempotent |

### Волна 5: Финализация

| # | Задача | Файл(ы) | Описание |
|---|--------|---------|----------|
| 11 | Integration-тесты API dashboard | `tests/integration/test_dashboard_api.py` | HTTP-тесты: GET /dashboard → 200 + structure; GET /forecast → 200 + curve; unauthenticated → 401 |
| 12 | Финализация | `docs/state.md`, `docs/progress.md` | Прогон pytest + ruff, обновление документации, финальный коммит |

## Порядок выполнения

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12
```

Задачи 2 и 4 можно делать параллельно (оба зависят только от 1).
Задачи 7-9 независимы от 2-6.
