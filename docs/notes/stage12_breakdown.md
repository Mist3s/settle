# Этап 12: Фронтенд — симулятор, аналитика, настройки

## Обзор

Этап заменяет страницы-заглушки (`simulator.tsx`, `settings.tsx`) полноценными экранами
и добавляет новый раздел аналитики. Три независимые фичи, каждая в своей директории
`features/simulator/`, `features/analytics/`, `features/settings/`.

**Зависимости:**
- Этап 8 (бэкенд симулятор) — API `/scenarios/*` готов, типы в `types/api.ts` есть.
- Этап 11 — все фронтенд экраны платёжного контура готовы.
- API-модули `api/scenarios.ts`, `api/settings.ts`, `api/import-export.ts` — готовы.

**Предварительные данные:**
- shadcn/ui компоненты: button, card, dialog, select, table, tabs, badge,
  input, label, separator, skeleton, progress, tooltip, sonner — все есть.
- Recharts — подключён (используется в ForecastChart, ScheduleChart).
- react-hook-form + zod — подключены и используются повсеместно.

---

## Волна 1: Инфраструктура

### Задача 1 — Добавление labels и утилит в format.ts
**Файл:** `src/lib/format.ts`  
**Что:** добавить `scenarioStatusLabel()`, `scenarioActionTypeLabel()`,
formatDays() для отображения diff дней.  
**~30 строк.**

### Задача 2 — Добавление shadcn/ui компонента textarea (для notes в формах)
**Файл:** `src/components/ui/textarea.tsx`  
**Что:** добавить через shadcn CLI или вручную.  
**~20 строк.**

---

## Волна 2: Симулятор — hooks и список сценариев

### Задача 3 — features/simulator/hooks.ts
**Файл:** `src/features/simulator/hooks.ts`  
**Что:** TanStack Query хуки:
- `useScenarios(status?)` — список сценариев
- `useScenario(id)` — один сценарий
- `useScenarioForecast(id, from, to, startingBalance)` — прогноз as-is/to-be
- `useCreateScenario`, `useUpdateScenario`, `useDeleteScenario` — мутации
- `useAddAction`, `useUpdateAction`, `useDeleteAction` — мутации действий
- `useApplyScenario`, `useArchiveScenario` — мутации применения  
**~150 строк.**

### Задача 4 — features/simulator/scenario-list.tsx
**Файл:** `src/features/simulator/scenario-list.tsx`  
**Что:** список карточек сценариев с badge статуса (draft/applied/archived),
фильтр по статусу, кнопка «Новый сценарий» → dialog, выбор текущего.  
**~150 строк.**

### Задача 5 — features/simulator/scenario-form-dialog.tsx
**Файл:** `src/features/simulator/scenario-form-dialog.tsx`  
**Что:** Dialog создания/редактирования сценария (name + base_date).
react-hook-form + zod.  
**~120 строк.**

---

## Волна 3: Симулятор — редактор действий

### Задача 6 — features/simulator/action-card.tsx
**Файл:** `src/features/simulator/action-card.tsx`  
**Что:** карточка действия сценария: тип (label), loan name, дата, params,
кнопки «Редактировать» / «Удалить».  
**~100 строк.**

### Задача 7 — features/simulator/action-form-dialog.tsx
**Файл:** `src/features/simulator/action-form-dialog.tsx`  
**Что:** Dialog добавления/редактирования действия. Select action_type,
динамические поля по типу:
- close_early_full: loan select, date
- prepayment_partial: loan select, date, amount
- reduce_payment: planned_payment select, new_amount
- skip: planned_payment select
- add_income: date, amount, name
- change_payment_date: planned_payment select, new_date  
**~250 строк** (самый большой компонент, wizard-like).

---

## Волна 4: Симулятор — сравнение и страница

### Задача 8 — features/simulator/comparison-view.tsx
**Файл:** `src/features/simulator/comparison-view.tsx`  
**Что:** два графика Recharts (as-is vs to-be AreaChart), числовая
разница (total_paid_difference, total_interest_saved,
first_zero_balance_date_change).
Responsive: side-by-side на desktop, табы на mobile.  
**~200 строк.**

### Задача 9 — pages/simulator.tsx (замена заглушки)
**Файл:** `src/pages/simulator.tsx`  
**Что:** двухпанельный layout:
- Слева: ScenarioList → при выборе: список ActionCard + кнопки
  «Добавить действие», «Применить», «Архивировать»
- Справа: ComparisonView (или пустое состояние)
- Мобайл: табы «Сценарии» / «Сравнение»
- Starting balance input  
**~180 строк.**

---

## Волна 5: Настройки

### Задача 10 — features/settings/hooks.ts
**Файл:** `src/features/settings/hooks.ts`  
**Что:** `useSettings()`, `useUpdateSettings()`, `useDownloadTemplate()`,
`useUploadImport()`, `useCommitImport()`, `useExportExcel()`.  
**~100 строк.**

### Задача 11 — features/settings/settings-form.tsx
**Файл:** `src/features/settings/settings-form.tsx`  
**Что:** форма настроек: key-value pairs (usd_rub_rate, unavailable_balance,
utilities_amount, etc.) сгруппированные по категориям.
react-hook-form, dynamic fields.  
**~180 строк.**

### Задача 12 — features/settings/import-export-section.tsx
**Файл:** `src/features/settings/import-export-section.tsx`  
**Что:** секция импорта/экспорта на странице настроек:
- Кнопка «Скачать шаблон» (пустой / с примерами)
- Drag-n-drop upload → dry-run отчёт → подтверждение commit
- Кнопка «Экспорт XLSX»
- Отображение DryRunReport (errors, warnings, summary)  
**~220 строк.**

### Задача 13 — pages/settings.tsx (замена заглушки)
**Файл:** `src/pages/settings.tsx`  
**Что:** tabs «Параметры» / «Импорт и экспорт»  
**~60 строк.**

---

## Волна 6: Аналитика

### Задача 14 — features/analytics/hooks.ts
**Файл:** `src/features/analytics/hooks.ts`  
**Что:** хуки для аналитики. Используют данные из существующих API
(loans, payments, schedule). Локальные вычисления:
- `usePaymentBreakdown(from, to)` — структура выплат (тело vs проценты)
- `useDebtByCreditor()` — разбивка долга по кредиторам
- `useOptimizer()` — рекомендация по методу лавины  
**~120 строк.**

### Задача 15 — features/analytics/payment-breakdown-chart.tsx
**Файл:** `src/features/analytics/payment-breakdown-chart.tsx`  
**Что:** stacked bar по месяцам (тело vs проценты vs рассрочки).
Recharts BarChart.  
**~120 строк.**

### Задача 16 — features/analytics/debt-breakdown-chart.tsx
**Файл:** `src/features/analytics/debt-breakdown-chart.tsx`  
**Что:** pie chart разбивка по кредиторам/типам. Recharts PieChart.  
**~100 строк.**

### Задача 17 — features/analytics/optimizer.tsx
**Файл:** `src/features/analytics/optimizer.tsx`  
**Что:** таблица рекомендаций: сортировка кредитов по ставке (avalanche),
показ экономии процентов при досрочном погашении высокоставочных первыми.  
**~130 строк.**

### Задача 18 — pages/analytics.tsx + роутинг
**Файл:** `src/pages/analytics.tsx`, обновление `routes/index.tsx`,
sidebar/mobile-nav.  
**Что:** страница аналитики с тремя секциями.
Добавить route `/analytics` и навигацию.  
**~80 строк (страница) + обновление 3 файлов.**

---

## Волна 7: Финальная верификация

### Задача 19 — tsc + ESLint + build
**Что:** `tsc --noEmit`, ESLint, production build.  
Фикс всех ошибок и warnings.

### Задача 20 — обновление docs
**Что:** обновить `docs/state.md`, `docs/progress.md`.  
Финальный коммит `feat(frontend): complete stage 12`.

---

## Оценка объёма

| Волна | Файлы | Строки | Описание |
|-------|-------|--------|----------|
| 1 | 2 | ~50 | Инфраструктура |
| 2 | 3 | ~420 | Симулятор: hooks, список, форма |
| 3 | 2 | ~350 | Симулятор: действия |
| 4 | 2 | ~380 | Симулятор: сравнение, страница |
| 5 | 4 | ~560 | Настройки |
| 6 | 5 | ~550 | Аналитика |
| 7 | — | — | Верификация, docs |
| **Итого** | **~18** | **~2310** | |
