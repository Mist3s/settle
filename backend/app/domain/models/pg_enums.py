"""PostgreSQL ENUM type definitions.

Centralized so each enum type is defined once and reused across models.
`create_type=False` because enums are created explicitly in the migration.
`values_callable` ensures lowercase values from Python enum `.value` are used,
not uppercase `.name`.
"""

from sqlalchemy.dialects.postgresql import ENUM

from app.domain.enums import (
    ActualPaymentType,
    AuditAction,
    BalanceSource,
    IncomeStatus,
    LoanStatus,
    LoanType,
    PaymentAccuracy,
    PaymentMethod,
    PaymentStatus,
    PrepaymentStrategy,
    ScenarioActionType,
    ScenarioStatus,
)

_values = lambda enum_cls: [e.value for e in enum_cls]  # noqa: E731

pg_loan_type = ENUM(
    LoanType, name="loan_type", create_type=False, values_callable=_values
)
pg_loan_status = ENUM(
    LoanStatus, name="loan_status", create_type=False, values_callable=_values
)
pg_payment_method = ENUM(
    PaymentMethod, name="payment_method", create_type=False, values_callable=_values
)
pg_payment_status = ENUM(
    PaymentStatus, name="payment_status", create_type=False, values_callable=_values
)
pg_payment_accuracy = ENUM(
    PaymentAccuracy, name="payment_accuracy", create_type=False, values_callable=_values
)
pg_actual_payment_type = ENUM(
    ActualPaymentType, name="actual_payment_type", create_type=False, values_callable=_values
)
pg_income_status = ENUM(
    IncomeStatus, name="income_status", create_type=False, values_callable=_values
)
pg_balance_source = ENUM(
    BalanceSource, name="balance_source", create_type=False, values_callable=_values
)
pg_prepayment_strategy = ENUM(
    PrepaymentStrategy, name="prepayment_strategy", create_type=False, values_callable=_values
)
pg_scenario_action_type = ENUM(
    ScenarioActionType, name="scenario_action_type", create_type=False, values_callable=_values
)
pg_scenario_status = ENUM(
    ScenarioStatus, name="scenario_status", create_type=False, values_callable=_values
)
pg_audit_action = ENUM(
    AuditAction, name="audit_action", create_type=False, values_callable=_values
)
