# Этап 8: Симулятор overlay (бэкенд) — декомпозиция

Объём: ~6 файлов, ожидается >600 строк суммарно. Разбивка на atomic-задачи.

## Архитектурные решения

- **Overlay в памяти**, НЕ в БД (architecture §6, §2 принцип 4).
- `simulation_service.py` разбивается на пакет `services/simulation/` если >400 строк.
- Forecast overlay: вызов `forecast_balance_by_day` с modified state (без session queries).
- Материализация (`apply`): каждое действие вызывает существующий `PaymentService` / прямую запись.

## Пакет `services/simulation/`

| Модуль | Ответственность | Строк (оценка) |
|--------|----------------|-----------------|
| `projected_state.py` | Dataclass ProjectedState — in-memory копия pending payments + expected incomes + loan balances | ~80 |
| `actions.py` | Чистые функции apply_* для каждого типа действия | ~200 |
| `engine.py` | `build_forecast()` — as-is + to-be + diff | ~120 |
| `materializer.py` | `apply_scenario()` — материализация через PaymentService | ~150 |
| `__init__.py` | Реэкспорт | ~10 |

## Задачи

| # | Задача | Файлы | Зависит от |
|---|--------|-------|-----------|
| 1 | Pydantic-схемы: params validators, ProjectedState, ScenarioForecastResponse, ScenarioForecastDiff | `domain/schemas/simulation.py` | — |
| 2 | ProjectedState dataclass — in-memory snapshot loader | `services/simulation/projected_state.py` | 1 |
| 3 | Action handlers: все 6 типов (чистые функции) | `services/simulation/actions.py` | 2 |
| 4 | Unit-тесты action handlers | `tests/unit/test_simulation_actions.py` | 3 |
| 5 | Forecast engine: build_forecast (as-is, to-be, diff) | `services/simulation/engine.py` | 3 |
| 6 | Materializer: apply_scenario, archive_scenario | `services/simulation/materializer.py` | 3 |
| 7 | Params JSONB validation по типу действия (Pydantic discriminated) | Расширение `domain/schemas/scenario.py` | 1 |
| 8 | Router: GET /forecast, POST /apply, POST /archive | Расширение `api/routers/scenarios.py` | 5, 6, 7 |
| 9 | Integration-тесты: forecast + invariant (overlay не пишет в БД) | `tests/integration/test_simulation_forecast.py` | 8 |
| 10 | Integration-тесты: apply + archive | `tests/integration/test_simulation_apply.py` | 8 |
| 11 | Финализация: ruff, pytest, docs update | — | 9, 10 |

## Волны

- **Волна 1** (задачи 1–2): схемы + projected state
- **Волна 2** (задачи 3–4): action handlers + unit-тесты
- **Волна 3** (задачи 5–7): engine + materializer + params validation
- **Волна 4** (задачи 8–10): router + integration-тесты
- **Волна 5** (задача 11): финализация
