/**
 * TypeScript types mirroring backend Pydantic schemas.
 * All monetary amounts are strings to preserve precision.
 * All dates are ISO 8601 strings (YYYY-MM-DD).
 * All datetimes are ISO 8601 UTC strings.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type LoanType = "credit" | "installment" | "split" | "utilities" | "other_debt";
export type LoanStatus = "active" | "paid_off" | "defaulted" | "cancelled";
export type PaymentMethod = "annuity" | "differentiated" | "installment" | "split" | "one_time";
export type PaymentStatus = "pending" | "paid" | "partial" | "skipped" | "cancelled" | "overdue";
export type PaymentAccuracy = "exact_contract" | "exact_screenshot" | "calculated_annuity" | "estimate";
export type ActualPaymentType = "regular" | "early_partial" | "early_full" | "overpayment" | "underpayment" | "missed";
export type IncomeStatus = "expected" | "received" | "cancelled";
export type BalanceSource = "manual" | "imported" | "calculated";
export type PrepaymentStrategy = "reduce_payment" | "shorten_term";
export type ScenarioActionType = "close_early_full" | "prepayment_partial" | "reduce_payment" | "skip" | "add_income" | "change_payment_date";
export type ScenarioStatus = "draft" | "applied" | "archived";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

// ---------------------------------------------------------------------------
// Loan
// ---------------------------------------------------------------------------

export interface LoanCreate {
  code: string;
  creditor: string;
  name: string;
  loan_type: LoanType;
  payment_method: PaymentMethod;
  original_amount?: string | null;
  interest_rate?: string;
  opening_date?: string | null;
  closing_date?: string | null;
  prepayment_strategy?: PrepaymentStrategy;
  priority?: number | null;
  status?: LoanStatus;
  contract_number?: string | null;
  notes?: string | null;
  late_fee_rate?: string | null;
  months_remaining?: number | null;
  payment_day?: number | null;
}

export interface LoanUpdate {
  code?: string | null;
  creditor?: string | null;
  name?: string | null;
  loan_type?: LoanType | null;
  payment_method?: PaymentMethod | null;
  original_amount?: string | null;
  interest_rate?: string | null;
  opening_date?: string | null;
  closing_date?: string | null;
  prepayment_strategy?: PrepaymentStrategy | null;
  priority?: number | null;
  status?: LoanStatus | null;
  contract_number?: string | null;
  notes?: string | null;
  late_fee_rate?: string | null;
  months_remaining?: number | null;
  payment_day?: number | null;
}

export interface LoanResponse {
  id: string;
  user_id: string;
  code: string;
  creditor: string;
  name: string;
  loan_type: LoanType;
  payment_method: PaymentMethod;
  original_amount: string | null;
  interest_rate: string;
  opening_date: string | null;
  closing_date: string | null;
  prepayment_strategy: PrepaymentStrategy;
  priority: number | null;
  status: LoanStatus;
  contract_number: string | null;
  notes: string | null;
  late_fee_rate: string | null;
  months_remaining: number | null;
  payment_day: number | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Balance
// ---------------------------------------------------------------------------

export interface BalanceCreate {
  amount: string;
  principal_balance?: string | null;
  snapshot_date: string;
  source?: BalanceSource;
  notes?: string | null;
}

export interface BalanceResponse {
  id: string;
  loan_id: string;
  snapshot_date: string;
  current_balance: string;
  principal_balance: string;
  accrued_interest: string;
  source: BalanceSource;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// PlannedPayment
// ---------------------------------------------------------------------------

export interface PlannedPaymentUpdate {
  due_date?: string | null;
  amount?: string | null;
  principal_part?: string | null;
  interest_part?: string | null;
  status?: PaymentStatus | null;
  accuracy?: PaymentAccuracy | null;
  income_id?: string | null;
  can_pay_early?: boolean | null;
  notes?: string | null;
}

export interface PlannedPaymentResponse {
  id: string;
  user_id: string;
  loan_id: string;
  income_id: string | null;
  due_date: string;
  amount: string;
  principal_part: string | null;
  interest_part: string | null;
  status: PaymentStatus;
  accuracy: PaymentAccuracy;
  can_pay_early: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// ActualPayment
// ---------------------------------------------------------------------------

export interface ActualPaymentCreate {
  loan_id: string;
  planned_payment_id?: string | null;
  amount: string;
  principal_part?: string | null;
  interest_part?: string | null;
  payment_date: string;
  payment_type: ActualPaymentType;
  notes?: string | null;
}

export interface ActualPaymentResponse {
  id: string;
  loan_id: string;
  planned_payment_id: string | null;
  amount: string;
  principal_part: string | null;
  interest_part: string | null;
  payment_date: string;
  payment_type: ActualPaymentType;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Income
// ---------------------------------------------------------------------------

export interface IncomeCreate {
  code: string;
  expected_date: string;
  amount: string;
  name?: string | null;
  status?: IncomeStatus;
  notes?: string | null;
}

export interface IncomeUpdate {
  code?: string | null;
  expected_date?: string | null;
  amount?: string | null;
  name?: string | null;
  status?: IncomeStatus | null;
  notes?: string | null;
}

export interface IncomeResponse {
  id: string;
  user_id: string;
  code: string;
  expected_date: string;
  amount: string;
  name: string | null;
  status: IncomeStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Scenario
// ---------------------------------------------------------------------------

export interface ScenarioCreate {
  name: string;
  base_date: string;
}

export interface ScenarioUpdate {
  name?: string | null;
  base_date?: string | null;
  status?: ScenarioStatus | null;
}

export interface ScenarioResponse {
  id: string;
  user_id: string;
  name: string;
  base_date: string;
  status: ScenarioStatus;
  created_at: string;
  updated_at: string;
}

export interface ScenarioActionCreate {
  action_type: ScenarioActionType;
  loan_id?: string | null;
  income_id?: string | null;
  planned_payment_id?: string | null;
  effective_date: string;
  params?: Record<string, unknown> | null;
}

export interface ScenarioActionUpdate {
  action_type?: ScenarioActionType | null;
  loan_id?: string | null;
  income_id?: string | null;
  planned_payment_id?: string | null;
  effective_date?: string | null;
  params?: Record<string, unknown> | null;
}

export interface ScenarioActionResponse {
  id: string;
  scenario_id: string;
  action_type: ScenarioActionType;
  loan_id: string | null;
  income_id: string | null;
  planned_payment_id: string | null;
  effective_date: string;
  params: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export interface SettingResponse {
  id: string;
  user_id: string;
  key: string;
  value: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface SettingItem {
  key: string;
  value: string;
  description?: string | null;
}

export interface SettingsUpdate {
  items: SettingItem[];
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface NextPayment {
  loan_id: string;
  loan_name: string;
  creditor: string;
  due_date: string;
  amount: string;
  status: string;
  can_pay_early: boolean;
}

export interface CurrentPeriod {
  from_date: string;
  to_date: string;
  income: string;
  planned_payments_total: string;
  remaining_for_living: string;
  status: "comfortable" | "tight" | "deficit";
}

export interface DashboardTotals {
  total_debt: string;
  active_loans: number;
  month_to_month_change: string;
}

export interface DashboardWarning {
  type: string;
  message: string;
}

export interface DashboardResponse {
  next_payments: NextPayment[];
  current_period: CurrentPeriod;
  totals: DashboardTotals;
  warnings: DashboardWarning[];
}

// ---------------------------------------------------------------------------
// Forecast
// ---------------------------------------------------------------------------

export interface DailyBalance {
  date: string;
  balance: string;
}

export interface ForecastResponse {
  from_date: string;
  to_date: string;
  starting_balance: string;
  points: DailyBalance[];
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

export interface ProjectionPayment {
  loan_id: string;
  due_date: string;
  amount: string;
  status: string;
  kind: string;
}

export interface ProjectionData {
  balance_by_day: DailyBalance[];
  payments: ProjectionPayment[];
}

export interface ScenarioForecastDiff {
  total_paid_difference: string;
  total_interest_saved: string;
  first_zero_balance_date_change: string | null;
}

export interface ScenarioForecastResponse {
  current: ProjectionData;
  scenario: ProjectionData;
  diff: ScenarioForecastDiff;
}

// ---------------------------------------------------------------------------
// Import/Export
// ---------------------------------------------------------------------------

export interface ImportError {
  sheet: string;
  row: number | null;
  column: string | null;
  message: string;
  severity: "error" | "warning";
}

export interface EntityDiff {
  entity_type: string;
  to_create: number;
  to_update: number;
}

export interface DryRunSummary {
  loans: EntityDiff;
  balances: EntityDiff;
  schedule: EntityDiff & { to_cancel_existing: number };
  incomes: EntityDiff;
  actual_payments: EntityDiff;
}

export interface DryRunReport {
  import_id: string;
  expires_at: string;
  summary: DryRunSummary;
  errors: ImportError[];
  warnings: ImportError[];
}

export interface CommitResult {
  created: number;
  updated: number;
  errors: string[];
}
