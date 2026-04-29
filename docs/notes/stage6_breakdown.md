# Этап 6: Atomic Breakdown

> Спецификация (маппинг DTO→ORM, кросс-валидация, dry-run отчёт, USD→RUB) — в [stage6_import_export.md](stage6_import_export.md).

## Структура пакета `services/import_/`

```
services/import_/
├── __init__.py          # public API: run_dry_run(), commit_import()
├── parser.py            # XLSX → DTO (openpyxl)
├── header_validator.py  # проверка имён колонок vs спецификация
├── cross_validator.py   # кросс-валидация между листами (ссылочная целостность)
├── diff.py              # сравнение DTO с БД → create/update отчёт
├── committer.py         # upsert в транзакции + audit_log + schedule-side-effects
└── storage.py           # in-memory dry-run store с TTL
```

## Таблица задач

| № | Файл | Ответственность | Зависит от | Сложность | ~Строк |
|---|------|-----------------|------------|-----------|--------|
| 1 | `services/import_/storage.py` | In-memory dict с TTL 30 мин, lazy GC, get/put/expire | — | S | 40–60 |
| 2 | `services/import_/header_validator.py` | Эталонные наборы колонок для 6 листов; `validate_headers(sheet_name, actual_cols) → list[ImportError]`; проверка обязательных листов | — | S | 50–80 |
| 3 | `services/import_/parser.py` | `parse_workbook(file_bytes) → ParsedData`; чтение листов openpyxl → список DTO; сбор ошибок с координатами (лист, строка, колонка); пропуск example-строк | №2 (header_validator), import_dto.py | M | 120–160 |
| 4 | `services/import_/cross_validator.py` | `cross_validate(parsed: ParsedData) → list[ImportError]`; 6 правил из спеки (loan_code→Loans, income_code→Incomes, balance per loan, principal+accrued=current, future date, enum) | import_dto.py | S | 80–120 |
| 5 | `domain/schemas/import_report.py` | Pydantic-схемы dry-run отчёта: `EntityDiff`, `DryRunSummary`, `DryRunReport`, `ImportError`, `ImportWarning` | — | S | 50–70 |
| 6 | `services/import_/diff.py` | `build_diff(session, user_id, parsed) → DryRunReport`; поиск по бизнес-ключам → create vs update; Income USD→RUB пересчёт; Settings lookup | №5 (import_report), repository layer | M | 120–160 |
| 7a | `services/import_/committer_core.py` | `CommitResult` dataclass + shared `_upsert_with_audit()` helper | — | S | 50–70 |
| 7b | `services/import_/committer_loans.py` | `_commit_settings`, `_commit_loans`, `_commit_balances` | №7a, №5, №6, audit_service | M | 150–180 |
| 7c | `services/import_/committer_payments.py` | `_commit_incomes`, `_cancel_pending_schedule`, `_commit_schedule`, `_commit_actual_payments`, `_auto_generate_schedules` | №7a, №5, №6, schedule_service, audit_service | M | 180–220 |
| 7d | `services/import_/committer.py` | `commit_import()` facade: orchestrates 7b + 7c in order | №7a, №7b, №7c | S | 40–60 |
| 8 | `services/import_/__init__.py` | Public API: `run_dry_run(session, user_id, file_bytes)`, `commit_import(session, user_id, import_id)`; оркестрация parse→validate→cross_validate→diff→store / store.get→commit | №1–7 | S | 60–90 |
| 9 | `services/export_service.py` | **Уже реализован** (212 строк). Ревью + мелкие правки если нужно | — | S | — |
| 10 | `services/template_service.py` | **Уже реализован** (118 строк). Ревью + мелкие правки если нужно | — | S | — |
| 11 | `api/routers/import_data.py` | 4 эндпоинта: `POST /import/excel`, `POST /import/excel/commit`, `GET /import/template`, `GET /export/excel`; тонкий HTTP-слой, multipart upload | №8, №9, №10 | S | 80–120 |
| 12 | `app/main.py` (правка) | Подключение `import_data` роутера | №11 | S | 3–5 |
| 13 | `app/cli.py` | CLI: `template`, `import --file --user --dry-run/--commit`, `export --user`; через typer/click или argparse | №8, №9, №10 | M | 100–140 |
| 14 | `tests/unit/test_import_dto.py` | Unit-тесты на DTO парсинг: _parse_decimal, _parse_bool, _parse_date, каждая модель, extra='forbid' | import_dto.py | S | 80–120 |
| 15 | `tests/unit/test_header_validator.py` | Unit-тесты: верные заголовки, лишние колонки, отсутствующие, обязательные листы | №2 | S | 40–60 |
| 16 | `tests/unit/test_cross_validator.py` | Unit-тесты: все 6 правил кросс-валидации, happy path + каждое нарушение | №4 | S | 80–120 |
| 17 | `tests/unit/test_import_storage.py` | Unit-тесты: put/get, expiry, lazy GC | №1 | S | 30–50 |
| 18 | `tests/unit/test_import_parser.py` | Unit-тесты: parse_workbook с fixture XLSX (happy path, ошибки строк, пропуск example row) | №3 | M | 80–120 |
| 19 | `tests/integration/test_import_diff.py` | Integration-тесты: diff с пустой БД (всё create), diff с existing (create+update), USD→RUB пересчёт | №6 | M | 100–140 |
| 20 | `tests/integration/test_import_commit.py` | Integration-тесты: commit, audit_log проверка, cancel pending, auto-generate schedule | №7 | M | 120–160 |
| 21 | `tests/integration/test_import_idempotency.py` | Integration: двойной прогон → идентичная БД; export→import→compare | №8, №9 | M | 80–120 |
| 22 | `tests/integration/test_import_api.py` | Integration: эндпоинты через TestClient, multipart upload, commit flow, template download, export download | №11 | M | 100–140 |
| 23 | `tests/fixtures/import_fixtures.py` | Хелперы для создания тестовых XLSX-файлов (openpyxl in-memory); factory-функции для наборов DTO | — | S | 60–100 |

## Порядок выполнения

Задачи сгруппированы в волны — внутри волны порядок любой, между волнами — строгая последовательность.

### Волна 1: Фундамент (нет зависимостей)

1. [№5] `domain/schemas/import_report.py` — схемы отчёта
2. [№1] `services/import_/storage.py` — хранилище dry-run
3. [№2] `services/import_/header_validator.py` — валидация заголовков
4. [№23] `tests/fixtures/import_fixtures.py` — тестовые хелперы

### Волна 2: Парсинг и валидация (зависит от волны 1)

5. [№3] `services/import_/parser.py` — XLSX→DTO
6. [№4] `services/import_/cross_validator.py` — кросс-валидация

### Волна 3: Unit-тесты на волны 1–2

7. [№14] `tests/unit/test_import_dto.py`
8. [№15] `tests/unit/test_header_validator.py`
9. [№16] `tests/unit/test_cross_validator.py`
10. [№17] `tests/unit/test_import_storage.py`
11. [№18] `tests/unit/test_import_parser.py`

### Волна 4: Diff и Commit (ядро бизнес-логики)

12. [№6] `services/import_/diff.py` — сравнение с БД
13. [№7a] `services/import_/committer_core.py` — CommitResult + shared helper
14. [№7b] `services/import_/committer_loans.py` — loans + balances + settings
15. [№7c] `services/import_/committer_payments.py` — incomes + schedule + actual_payments
16. [№7d] `services/import_/committer.py` — facade

### Волна 5: Оркестратор

14. [№8] `services/import_/__init__.py` — public API пакета

### Волна 6: Ревью существующего

15. [№9] `services/export_service.py` — ревью
16. [№10] `services/template_service.py` — ревью

### Волна 7: HTTP и CLI

17. [№11] `api/routers/import_data.py` — REST эндпоинты
18. [№12] `app/main.py` — подключение роутера
19. [№13] `app/cli.py` — CLI команды

### Волна 8: Integration-тесты

20. [№19] `tests/integration/test_import_diff.py`
21. [№20] `tests/integration/test_import_commit.py`
22. [№21] `tests/integration/test_import_idempotency.py`
23. [№22] `tests/integration/test_import_api.py`

## Замечания

- **Тесты идут отдельными задачами**, но в рамках коммитов объединяются с кодом: модуль + его тест = один коммит.
- **committer** — разбит на 4 модуля (7a–7d): `committer_core.py` (~60 строк), `committer_loans.py` (~170 строк), `committer_payments.py` (~210 строк), `committer.py` facade (~50 строк). Причина: monolith был ~580 строк из-за repetitive audit boilerplate.
- **export_service.py** и **template_service.py** уже готовы и прошли линтер. Ревью = прочитать, убедиться в совместимости с пакетом import_, при необходимости добавить общие константы в shared модуль.
