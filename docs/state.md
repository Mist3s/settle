# Состояние проекта Settle

**Последнее обновление:** 2026-04-29

## Текущий этап

**Этап 6: Импорт и экспорт данных** — в работе.

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

## Этап 6: что готово

- **DTO** (`domain/schemas/import_dto.py`): 6 Pydantic-моделей для листов XLSX-шаблона:
  - `SettingImportRow`, `LoanImportRow`, `BalanceImportRow`, `ScheduleImportRow`, `IncomeImportRow`, `ActualPaymentImportRow`
  - Хелперы: `_parse_decimal` (запятая→точка, неразрывные пробелы), `_parse_bool` (true/false/1/0/yes/no/да/нет), `_parse_date` (ISO + Excel serial)
  - Все модели с `extra='forbid'`

## Этап 6: что осталось реализовать

Детальная декомпозиция: [docs/notes/stage6_breakdown.md](notes/stage6_breakdown.md).
Спецификация: [docs/notes/stage6_import_export.md](notes/stage6_import_export.md).

### Готово

- `domain/schemas/import_dto.py` — 6 DTO моделей для листов XLSX
- `domain/schemas/import_report.py` — 7 Pydantic-моделей dry-run отчёта (92 строки)
- `services/export_service.py` — экспорт в XLSX (212 строк)
- `services/template_service.py` — генерация шаблона (118 строк)

### Осталось (23 atomic-задачи, 8 волн)

Import-сервис разбит на пакет `services/import_/` с модулями:
`storage`, `header_validator`, `parser`, `cross_validator`, `diff`, `committer`, `__init__`.

Полный перечень задач, зависимостей и порядок — в stage6_breakdown.md.

## Ключевые факты для реализации (VERIFIED)

### Бизнес-ключи (architecture.md §11.4)
| Сущность | Бизнес-ключ | Поведение |
|----------|-------------|-----------|
| Loan | `code` | Все поля обновляются |
| Balance | `(loan_code, snapshot_date)` | Все поля обновляются |
| Schedule | `(loan_code, due_date)` | Все поля обновляются |
| Income | `code` | Все поля обновляются |
| ActualPayment | `(loan_code, payment_date, amount)` | Все поля обновляются |

### ORM-модели: поля для поиска по бизнес-ключу
- `Loan`: `code` (String(32)), `user_id` (UUID), unique constraint `uq_loans_user_id_code`
- `LoanBalance`: `loan_id` (UUID), `snapshot_date` (Date), unique constraint `uq_loan_balances_loan_id_snapshot_date`
- `PlannedPayment`: `loan_id` + `due_date`, нет unique constraint (нужен поиск вручную)
- `Income`: `code` (String(64)), unique=True (глобально, не per-user)
- `ActualPayment`: `loan_id` + `payment_date` + `amount`, нет unique constraint
- `Setting`: `user_id` + `key`, unique constraint `uq_settings_user_id_key`

### Репозитории: доступный API
- `Repository.list(filters={...})` — фильтрация по атрибутам
- `Repository.create(**kwargs)` → flush + refresh
- `Repository.update(entity_id, **kwargs)` → flush + refresh
- `SettingsRepository.get_by_key(user_id, key)`
- `BalanceRepository.get_latest(loan_id)`

### Сервисный паттерн
- Функции модульного уровня (не классы), принимают `session: AsyncSession` + `user_id: uuid.UUID`
- Репозитории создаются внутри функций: `repo = LoanRepository(session)`
- Audit записывается через `audit_service.record(session, entity_type=..., entity_id=..., action=..., before_state=..., after_state=..., changed_by=...)`
- `audit_service.model_to_dict(instance)` — безопасная сериализация ORM

### API паттерн
- Роутеры в `api/routers/`, тонкий HTTP-слой
- `Depends(get_current_user)` для аутентификации, `Depends(get_session)` для БД
- Роутеры зависят только от сервисов и схем
- Decimal-конвертация в роутерах (str → Decimal)

### Архитектура: алгоритм импорта (§11.3)
1. Dry-run: загрузка XLSX → проверка 3 обязательных листов → валидация заголовков → парсинг строк → кросс-валидация → сравнение с БД → отчёт
2. Commit: по import_id → одна транзакция → audit_log → для Schedule: cancel existing pending → для кредитов без Schedule: ScheduleService
3. Dry-run результат хранится 30 мин, `import_id` = UUID

### Зависимости (pyproject.toml)
- `openpyxl` — уже в pyproject.toml (установлен на этапе 1)

## Следующий шаг

Продолжить волну 1 по [stage6_breakdown.md](notes/stage6_breakdown.md):
`storage.py`, `header_validator.py`, `import_fixtures.py`.
