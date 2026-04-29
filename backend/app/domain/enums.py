"""Python enums mirroring PostgreSQL enum types.

Each enum here maps 1:1 to a PostgreSQL enum created in migration 001.
Values are lowercase strings matching the DB enum labels exactly.
"""

import enum


class LoanType(str, enum.Enum):
    CREDIT = "credit"
    INSTALLMENT = "installment"
    SPLIT = "split"
    UTILITIES = "utilities"
    OTHER_DEBT = "other_debt"


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    PAID_OFF = "paid_off"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    ANNUITY = "annuity"
    DIFFERENTIATED = "differentiated"
    INSTALLMENT = "installment"
    SPLIT = "split"
    ONE_TIME = "one_time"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class PaymentAccuracy(str, enum.Enum):
    EXACT_CONTRACT = "exact_contract"
    EXACT_SCREENSHOT = "exact_screenshot"
    CALCULATED_ANNUITY = "calculated_annuity"
    ESTIMATE = "estimate"


class ActualPaymentType(str, enum.Enum):
    REGULAR = "regular"
    EARLY_PARTIAL = "early_partial"
    EARLY_FULL = "early_full"
    OVERPAYMENT = "overpayment"
    UNDERPAYMENT = "underpayment"
    MISSED = "missed"


class IncomeStatus(str, enum.Enum):
    EXPECTED = "expected"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class BalanceSource(str, enum.Enum):
    MANUAL = "manual"
    IMPORTED = "imported"
    CALCULATED = "calculated"


class PrepaymentStrategy(str, enum.Enum):
    REDUCE_PAYMENT = "reduce_payment"
    SHORTEN_TERM = "shorten_term"


class ScenarioActionType(str, enum.Enum):
    CLOSE_EARLY_FULL = "close_early_full"
    PREPAYMENT_PARTIAL = "prepayment_partial"
    REDUCE_PAYMENT = "reduce_payment"
    SKIP = "skip"
    ADD_INCOME = "add_income"
    CHANGE_PAYMENT_DATE = "change_payment_date"


class ScenarioStatus(str, enum.Enum):
    DRAFT = "draft"
    APPLIED = "applied"
    ARCHIVED = "archived"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
