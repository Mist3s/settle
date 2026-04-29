/**
 * Formatting utilities for money, dates, percentages and deltas.
 * Centralised source of truth — all UI components use these helpers.
 */

import { format, parseISO, isValid } from "date-fns";
import { ru } from "date-fns/locale";

// ---------------------------------------------------------------------------
// Money
// ---------------------------------------------------------------------------

const moneyFormatter = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const moneyCompactFormatter = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

/**
 * Format a monetary string (e.g. "15900.00") as "15 900,00 ₽".
 * Returns "—" for null/undefined/empty.
 */
export function formatMoney(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return moneyFormatter.format(n);
}

/**
 * Compact money — no decimals, e.g. "15 900 ₽".
 */
export function formatMoneyCompact(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return moneyCompactFormatter.format(n);
}

// ---------------------------------------------------------------------------
// Dates
// ---------------------------------------------------------------------------

/**
 * Format ISO date string "2026-05-10" → "10 мая 2026".
 */
export function formatDate(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const d = parseISO(value);
  if (!isValid(d)) return "—";
  return format(d, "d MMMM yyyy", { locale: ru });
}

/**
 * Short date: "10 мая".
 */
export function formatDateShort(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const d = parseISO(value);
  if (!isValid(d)) return "—";
  return format(d, "d MMM", { locale: ru });
}

/**
 * Chart-friendly date: "10.05".
 */
export function formatDateCompact(value: string | null | undefined): string {
  if (value == null || value === "") return "";
  const d = parseISO(value);
  if (!isValid(d)) return "";
  return format(d, "dd.MM", { locale: ru });
}

// ---------------------------------------------------------------------------
// Percentages
// ---------------------------------------------------------------------------

/**
 * Format annual rate "12.50" → "12,5%".
 */
export function formatPercent(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  // Remove trailing zeros: 12.50 → "12,5%", 0.00 → "0%"
  return n.toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }) + "%";
}

// ---------------------------------------------------------------------------
// Deltas
// ---------------------------------------------------------------------------

/**
 * Format a delta string (e.g. "-12000.00") as "−12 000 ₽" / "+5 000 ₽".
 * Returns null for zero. Used in month-to-month change displays.
 */
export function formatDelta(value: string | null | undefined): string | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n) || n === 0) return null;
  const abs = Math.abs(n);
  const formatted = moneyCompactFormatter.format(abs);
  return n < 0 ? `−${formatted}` : `+${formatted}`;
}

/**
 * CSS color class for a delta value.
 */
export function deltaColor(value: string | null | undefined): string {
  if (value == null || value === "") return "text-muted-foreground";
  const n = Number(value);
  if (Number.isNaN(n) || n === 0) return "text-muted-foreground";
  return n < 0 ? "text-success" : "text-danger";
}

// ---------------------------------------------------------------------------
// Loan type / status labels (Russian)
// ---------------------------------------------------------------------------

const LOAN_TYPE_LABELS: Record<string, string> = {
  credit: "Кредит",
  installment: "Рассрочка",
  split: "Сплит",
  utilities: "Коммунальные",
  other_debt: "Прочий долг",
};

const LOAN_STATUS_LABELS: Record<string, string> = {
  active: "Активный",
  paid_off: "Погашен",
  defaulted: "Дефолт",
  cancelled: "Отменён",
};

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  pending: "Ожидается",
  paid: "Оплачен",
  partial: "Частично",
  skipped: "Пропущен",
  cancelled: "Отменён",
  overdue: "Просрочен",
};

const ACCURACY_LABELS: Record<string, string> = {
  exact_contract: "Договор",
  exact_screenshot: "Скриншот",
  calculated_annuity: "Расчётный",
  estimate: "Оценка",
};

const INCOME_STATUS_LABELS: Record<string, string> = {
  expected: "Ожидается",
  received: "Получено",
  cancelled: "Отменено",
};

const ACTUAL_PAYMENT_TYPE_LABELS: Record<string, string> = {
  regular: "Регулярный",
  early_partial: "Досрочный частичный",
  early_full: "Досрочный полный",
  overpayment: "Переплата",
  underpayment: "Недоплата",
  missed: "Пропущен",
};

const LOAN_TYPE_COLORS: Record<string, string> = {
  credit: "bg-blue-500",
  installment: "bg-emerald-500",
  split: "bg-violet-500",
  utilities: "bg-gray-400",
  other_debt: "bg-red-500",
};

export function loanTypeLabel(type: string): string {
  return LOAN_TYPE_LABELS[type] ?? type;
}

export function loanStatusLabel(status: string): string {
  return LOAN_STATUS_LABELS[status] ?? status;
}

export function paymentStatusLabel(status: string): string {
  return PAYMENT_STATUS_LABELS[status] ?? status;
}

export function accuracyLabel(accuracy: string): string {
  return ACCURACY_LABELS[accuracy] ?? accuracy;
}

export function incomeStatusLabel(status: string): string {
  return INCOME_STATUS_LABELS[status] ?? status;
}

export function actualPaymentTypeLabel(type: string): string {
  return ACTUAL_PAYMENT_TYPE_LABELS[type] ?? type;
}

export function loanTypeColor(type: string): string {
  return LOAN_TYPE_COLORS[type] ?? "bg-gray-400";
}

// ---------------------------------------------------------------------------
// Scenario labels
// ---------------------------------------------------------------------------

const SCENARIO_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  applied: "Применён",
  archived: "Архив",
};

const SCENARIO_ACTION_TYPE_LABELS: Record<string, string> = {
  close_early_full: "Полное досрочное",
  prepayment_partial: "Частичное досрочное",
  reduce_payment: "Уменьшить платёж",
  skip: "Пропустить",
  add_income: "Добавить доход",
  change_payment_date: "Перенос даты",
};

export function scenarioStatusLabel(status: string): string {
  return SCENARIO_STATUS_LABELS[status] ?? status;
}

export function scenarioActionTypeLabel(type: string): string {
  return SCENARIO_ACTION_TYPE_LABELS[type] ?? type;
}

/**
 * Format a day-count string like "+12 days" / "-5 days" → "+12 дн." / "−5 дн."
 * Also handles raw number strings.
 */
export function formatDays(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const match = value.match(/^([+-]?)(\d+)/);
  if (!match) return value;
  const sign = match[1] === "-" ? "−" : match[1] === "+" ? "+" : "";
  return `${sign}${match[2]} дн.`;
}
