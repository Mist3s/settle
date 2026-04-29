# Заметки к этапу 6: Импорт и экспорт данных

## Декомпозиция на коммиты

### Коммит 1: import_service.py — парсинг + валидация
- Парсинг XLSX через openpyxl → DTO (import_dto.py уже готов)
- Валидация заголовков каждого листа
- Кросс-валидация ссылочной целостности
- Сбор ошибок с координатами (лист, строка, колонка)
- Без взаимодействия с БД — чистые функции

### Коммит 2: import_service.py — dry-run + commit
- Dry-run: сравнение DTO с БД по бизнес-ключам → create/update report
- Temporary storage (dict с TTL 30 мин)
- Commit: upsert в одной транзакции + audit_log
- Авто-генерация графика для кредитов без Schedule
- Отмена существующих pending planned при импорте Schedule

### Коммит 3: export_service.py + template_service.py
- Экспорт: 6 листов, данные из БД → XLSX
- Шаблон: пустой + с примерами

### Коммит 4: api/routers/import_data.py
- REST endpoints: upload, commit, template, export
- Подключение роутера в main.py

### Коммит 5: cli.py
- `python -m app.cli template/import/export`

### Коммит 6: тесты
- Unit: DTO парсинг, кросс-валидация
- Integration: идемпотентность, полный цикл, ошибки валидации

## Спецификация листов XLSX (из architecture.md §11.2)

### Обязательные листы: Settings, Loans, Balances
### Опциональные листы: Schedule, Incomes, ActualPayments

### Колонки (имена = ключи DTO)

**Settings:** key, value, description
**Loans:** code, creditor, name, loan_type, payment_method, original_amount, interest_rate, opening_date, closing_date, prepayment_strategy, priority, status, contract_number, notes
**Balances:** loan_code, snapshot_date, current_balance, principal_balance, accrued_interest, source, notes
**Schedule:** loan_code, due_date, amount, principal_part, interest_part, accuracy, can_pay_early, income_code, notes
**Incomes:** code, expected_date, amount_rub, amount_usd, name, status, notes
**ActualPayments:** loan_code, payment_date, amount, principal_part, interest_part, payment_type, planned_due_date, notes

## Маппинг DTO → ORM

### LoanImportRow → Loan
- code → code
- creditor → creditor
- name → name
- loan_type → loan_type
- payment_method → payment_method
- original_amount → original_amount
- interest_rate → interest_rate (default 0)
- opening_date → opening_date
- closing_date → closing_date
- prepayment_strategy → prepayment_strategy (default reduce_payment)
- priority → priority
- status → status (default active)
- contract_number → contract_number
- notes → notes
- **Добавить:** user_id (из контекста)

### BalanceImportRow → LoanBalance
- loan_code → нужен lookup Loan.id по code
- snapshot_date → snapshot_date
- current_balance → current_balance
- principal_balance → principal_balance (default = current_balance)
- accrued_interest → accrued_interest (default 0)
- source → source (default imported)
- notes → notes
- **Добавить:** loan_id (resolved)

### ScheduleImportRow → PlannedPayment
- loan_code → нужен lookup Loan.id по code
- due_date → due_date
- amount → amount
- principal_part → principal_part
- interest_part → interest_part
- accuracy → accuracy (default estimate)
- can_pay_early → can_pay_early (default true)
- income_code → нужен lookup Income.id по code → income_id
- notes → notes
- **Добавить:** loan_id, user_id, status='pending'

### IncomeImportRow → Income
- code → code
- expected_date → expected_date
- amount_rub → amount (если amount_usd → пересчёт по usd_rub_rate из Settings)
- amount_usd → amount (пересчёт)
- name → name
- status → status (default expected)
- notes → notes
- **Добавить:** user_id

### ActualPaymentImportRow → ActualPayment
- loan_code → нужен lookup Loan.id по code → loan_id
- payment_date → payment_date
- amount → amount
- principal_part → principal_part
- interest_part → interest_part
- payment_type → payment_type (если пусто → определяется автоматически)
- planned_due_date → нужен lookup PlannedPayment.id по (loan_id, due_date) → planned_payment_id
- notes → notes

## Кросс-валидация (§11.3 п.4)

1. Все loan_code в Balances/Schedule/ActualPayments → существуют в Loans
2. Все income_code в Schedule → существуют в Incomes (если оба листа заполнены)
3. Каждый Loan → имеет хотя бы один Balance
4. principal_balance + accrued_interest = current_balance (если все три заданы)
5. Balances.snapshot_date не в будущем
6. Enum значения из допустимого набора (Pydantic уже валидирует)

## Dry-run отчёт (§11.3 п.6)

```json
{
  "import_id": "uuid",
  "expires_at": "ISO datetime",
  "summary": {
    "loans": {"to_create": N, "to_update": N},
    "balances": {"to_create": N, "to_update": N},
    "schedule": {"to_create": N, "to_update": N, "to_cancel_existing": N},
    "incomes": {"to_create": N, "to_update": N},
    "actual_payments": {"to_create": N, "to_update": N}
  },
  "errors": [],
  "warnings": []
}
```

## Временное хранение dry-run

In-memory dict: `_dry_run_store: dict[UUID, DryRunResult]` с `expires_at`.
Cleanup при каждом обращении (ленивый GC). Достаточно для однопользовательского приложения.
Альтернатива — таблица в БД, но overhead не оправдан.

## Income amount: пересчёт USD → RUB

- Если задан `amount_usd` и не задан `amount_rub` → `amount = amount_usd * usd_rub_rate`
- `usd_rub_rate` берётся из Settings листа текущего импорта (или из БД, если Settings лист не содержит этот ключ)
- Если оба заданы → `amount_rub` приоритетнее (warning)
