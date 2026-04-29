# Этап 9: Фронтенд — каркас и дизайн-система

## Декомпозиция на atomic-задачи

Задачи упорядочены по зависимостям. Каждая — один коммит.

---

### Волна 0: Подготовка

**№1. Очистка boilerplate и установка shadcn/ui**
- Удалить `App.css` (Vite boilerplate, не используется).
- Установить `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react` — инфраструктурные зависимости shadcn/ui.
- Создать `src/lib/utils.ts` с `cn()` (clsx + twMerge).
- Создать `components.json` для shadcn CLI (если поддерживается), либо ручная структура `src/components/ui/`.

**Файлы:** `package.json`, `src/lib/utils.ts`, удалить `src/App.css`.

---

### Волна 1: Инфраструктура

**№2. TypeScript-типы, синхронизированные с бэкендом**
- `src/types/api.ts` — все response/request типы, соответствующие Pydantic-схемам бэкенда.
- Типы: Auth (LoginRequest, TokenResponse), Loan, Balance, PlannedPayment, ActualPayment, Income, Scenario, ScenarioAction, Settings, Dashboard, Forecast, DryRunReport.
- Все денежные поля — `string` (как в API).

**Файлы:** `src/types/api.ts`.

**№3. API-клиент с JWT-интерцептором**
- `src/api/client.ts` — axios instance.
- Request interceptor: добавляет `Authorization: Bearer <access_token>`.
- Response interceptor: при 401 → попытка refresh → retry; при неудаче → redirect на login.
- Токены хранятся в `localStorage` (access_token, refresh_token).
- `src/api/auth.ts` — login(), refresh(), logout().

**Файлы:** `src/api/client.ts`, `src/api/auth.ts`.

**№4. Zustand auth store**
- `src/stores/auth.ts` — AuthStore: `isAuthenticated`, `login()`, `logout()`, `checkAuth()`.
- `login()` сохраняет токены в localStorage, обновляет state.
- `logout()` чистит localStorage, сбрасывает state.
- `checkAuth()` — проверка наличия валидного access_token при инициализации.

**Файлы:** `src/stores/auth.ts`.

---

### Волна 2: Базовые UI-компоненты

**№5. shadcn/ui базовые компоненты**
- Ручная реализация (Tailwind 4 + Radix primitives где нужно):
  - `src/components/ui/button.tsx`
  - `src/components/ui/input.tsx`
  - `src/components/ui/card.tsx`
  - `src/components/ui/label.tsx`
  - `src/components/ui/separator.tsx`
  - `src/components/ui/skeleton.tsx`
- Стили адаптированы к Settle palette (primary, surface, success, warning, danger).

**Файлы:** `src/components/ui/` (6 файлов).

**№6. Toast (Sonner) и провайдер**
- `src/components/ui/sonner.tsx` — обёртка `<Toaster />` с Settle-стилями.
- Подключение в корневой layout.

**Файлы:** `src/components/ui/sonner.tsx`.

---

### Волна 3: Layout и роутинг

**№7. Layout компоненты**
- `src/components/layout/sidebar.tsx` — sidebar для desktop (>1024px): лого, навигация (Дашборд, Кредиты, Календарь, Симулятор, Настройки), иконки Lucide.
- `src/components/layout/mobile-nav.tsx` — bottom navigation для мобильных (<640px).
- `src/components/layout/header.tsx` — header: заголовок страницы, кнопка выхода.
- `src/components/layout/app-layout.tsx` — обёртка: sidebar + header + main content area.

**Файлы:** `src/components/layout/` (4 файла).

**№8. React Router + защищённые маршруты**
- `src/routes/index.tsx` — createBrowserRouter:
  - `/login` — публичный
  - `/` — redirect на `/dashboard`
  - `/dashboard` — защищённый
  - `/loans` — защищённый
  - `/calendar` — защищённый
  - `/simulator` — защищённый
  - `/settings` — защищённый
- `src/routes/protected-route.tsx` — проверка auth, redirect на /login.
- Страницы-заглушки: `src/pages/dashboard.tsx`, `src/pages/loans.tsx`, `src/pages/calendar.tsx`, `src/pages/simulator.tsx`, `src/pages/settings.tsx`.

**Файлы:** `src/routes/index.tsx`, `src/routes/protected-route.tsx`, `src/pages/` (5 заглушек).

---

### Волна 4: Login и сборка

**№9. Login-страница**
- `src/pages/login.tsx` — форма с react-hook-form + zod валидация.
- Поля: email, password.
- Визуально: центрирована, карточка, Settle branding, error handling.
- При успехе — redirect на /dashboard.

**Файлы:** `src/pages/login.tsx`.

**№10. Интеграция: App.tsx → Router + Layout + Sonner**
- Перестроить `src/App.tsx`: подключить RouterProvider.
- Обновить `src/main.tsx` если нужно.
- Vite proxy: настроить `server.proxy` для `/api` → `http://backend:8000` (чтобы не было CORS-проблем в dev).

**Файлы:** `src/App.tsx`, `src/main.tsx`, `vite.config.ts`.

---

### Волна 5: Финализация

**№11. API-модули по доменам**
- `src/api/loans.ts` — getLoans(), getLoan(), createLoan(), etc.
- `src/api/payments.ts` — getPlannedPayments(), registerPayment(), etc.
- `src/api/dashboard.ts` — getDashboard(), getForecast().
- `src/api/scenarios.ts` — getScenarios(), etc.
- `src/api/settings.ts` — getSettings(), updateSettings().
- `src/api/import-export.ts` — uploadExcel(), commitImport(), downloadTemplate(), exportExcel().
- Каждый модуль использует `client.ts` instance.

**Файлы:** `src/api/` (6 файлов).

**№12. Zustand UI store + hooks**
- `src/stores/ui.ts` — UIStore: sidebarOpen, currentPage, selectedLoanId, filters.
- `src/hooks/use-media-query.ts` — responsive helper.

**Файлы:** `src/stores/ui.ts`, `src/hooks/use-media-query.ts`.

**№13. Верификация и финализация**
- `tsc --noEmit` — без ошибок.
- Визуальная проверка: login → dashboard → навигация между страницами.
- Обновление `docs/state.md`, `docs/progress.md`.

---

## Граф зависимостей

```
№1 → №2, №5, №6
№2 → №3
№3 → №4
№4 → №9
№5 → №7
№6 → №10
№7 → №8
№8 → №10
№9 → №10
№10 → №11, №12
№11 + №12 → №13
```

## Итого: 13 задач в 6 волнах
