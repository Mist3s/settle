"""001_initial_schema

Revision ID: 3c0c449dc472
Revises:
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3c0c449dc472"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All PostgreSQL enum types used in the schema.
ENUM_TYPES = {
    "loan_type": ("credit", "installment", "split", "utilities", "other_debt"),
    "loan_status": ("active", "paid_off", "defaulted", "cancelled"),
    "payment_method": ("annuity", "differentiated", "installment", "split", "one_time"),
    "payment_status": ("pending", "paid", "partial", "skipped", "cancelled", "overdue"),
    "payment_accuracy": (
        "exact_contract", "exact_screenshot", "calculated_annuity", "estimate",
    ),
    "actual_payment_type": (
        "regular", "early_partial", "early_full",
        "overpayment", "underpayment", "missed",
    ),
    "income_status": ("expected", "received", "cancelled"),
    "balance_source": ("manual", "imported", "calculated"),
    "prepayment_strategy": ("reduce_payment", "shorten_term"),
    "scenario_action_type": (
        "close_early_full", "prepayment_partial", "reduce_payment",
        "skip", "add_income", "change_payment_date",
    ),
    "scenario_status": ("draft", "applied", "archived"),
    "audit_action": ("create", "update", "delete", "restore"),
}


def upgrade() -> None:
    # --- Create all enum types ---
    for name, values in ENUM_TYPES.items():
        sa.Enum(*values, name=name).create(op.get_bind(), checkfirst=True)

    # --- Tables ---
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("action", postgresql.ENUM("create", "update", "delete", "restore", name="audit_action", create_type=False), nullable=False),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("changed_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], name=op.f("fk_audit_log_changed_by_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index("ix_audit_log_entity_type_entity_id_changed_at", "audit_log", ["entity_type", "entity_id", "changed_at"], unique=False)

    op.create_table(
        "incomes",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("status", postgresql.ENUM("expected", "received", "cancelled", name="income_status", create_type=False), server_default="expected", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_incomes_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incomes")),
        sa.UniqueConstraint("code", name=op.f("uq_incomes_code")),
    )

    op.create_table(
        "loans",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("creditor", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("loan_type", postgresql.ENUM("credit", "installment", "split", "utilities", "other_debt", name="loan_type", create_type=False), nullable=False),
        sa.Column("payment_method", postgresql.ENUM("annuity", "differentiated", "installment", "split", "one_time", name="payment_method", create_type=False), nullable=False),
        sa.Column("original_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("interest_rate", sa.Numeric(precision=6, scale=4), server_default="0", nullable=False),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column("prepayment_strategy", postgresql.ENUM("reduce_payment", "shorten_term", name="prepayment_strategy", create_type=False), server_default="reduce_payment", nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("status", postgresql.ENUM("active", "paid_off", "defaulted", "cancelled", name="loan_status", create_type=False), server_default="active", nullable=False),
        sa.Column("contract_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("late_fee_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("months_remaining", sa.Integer(), nullable=True),
        sa.Column("payment_day", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("closing_date >= opening_date OR closing_date IS NULL OR opening_date IS NULL", name=op.f("ck_loans_closing_after_opening")),
        sa.CheckConstraint("interest_rate >= 0", name=op.f("ck_loans_positive_interest_rate")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_loans_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loans")),
        sa.UniqueConstraint("user_id", "code", name="uq_loans_user_id_code"),
    )
    op.create_index("ix_loans_user_id_status", "loans", ["user_id", "status"], unique=False)

    op.create_table(
        "scenarios",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_date", sa.Date(), nullable=False),
        sa.Column("status", postgresql.ENUM("draft", "applied", "archived", name="scenario_status", create_type=False), server_default="draft", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_scenarios_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenarios")),
    )

    op.create_table(
        "settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_settings_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settings")),
        sa.UniqueConstraint("user_id", "key", name="uq_settings_user_id_key"),
    )

    op.create_table(
        "loan_balances",
        sa.Column("loan_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("current_balance", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("principal_balance", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("accrued_interest", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("source", postgresql.ENUM("manual", "imported", "calculated", name="balance_source", create_type=False), server_default="imported", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("accrued_interest >= 0", name=op.f("ck_loan_balances_non_negative_interest")),
        sa.CheckConstraint("principal_balance >= 0", name=op.f("ck_loan_balances_non_negative_principal")),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], name=op.f("fk_loan_balances_loan_id_loans"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loan_balances")),
        sa.UniqueConstraint("loan_id", "snapshot_date", name="uq_loan_balances_loan_id_snapshot_date"),
    )

    op.create_table(
        "planned_payments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("loan_id", sa.UUID(), nullable=False),
        sa.Column("income_id", sa.UUID(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("principal_part", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("interest_part", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "paid", "partial", "skipped", "cancelled", "overdue", name="payment_status", create_type=False), server_default="pending", nullable=False),
        sa.Column("accuracy", postgresql.ENUM("exact_contract", "exact_screenshot", "calculated_annuity", "estimate", name="payment_accuracy", create_type=False), server_default="estimate", nullable=False),
        sa.Column("can_pay_early", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name=op.f("ck_planned_payments_positive_amount")),
        sa.ForeignKeyConstraint(["income_id"], ["incomes.id"], name=op.f("fk_planned_payments_income_id_incomes"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], name=op.f("fk_planned_payments_loan_id_loans"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_planned_payments_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_planned_payments")),
    )
    op.create_index("ix_planned_payments_income_id", "planned_payments", ["income_id"], unique=False)
    op.create_index("ix_planned_payments_loan_id_due_date", "planned_payments", ["loan_id", "due_date"], unique=False)
    op.create_index("ix_planned_payments_user_id_due_date", "planned_payments", ["user_id", "due_date"], unique=False)

    op.create_table(
        "actual_payments",
        sa.Column("loan_id", sa.UUID(), nullable=False),
        sa.Column("planned_payment_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("principal_part", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("interest_part", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_type", postgresql.ENUM("regular", "early_partial", "early_full", "overpayment", "underpayment", "missed", name="actual_payment_type", create_type=False), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], name=op.f("fk_actual_payments_loan_id_loans"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["planned_payment_id"], ["planned_payments.id"], name=op.f("fk_actual_payments_planned_payment_id_planned_payments"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_actual_payments")),
    )
    op.create_index("ix_actual_payments_loan_id_payment_date", "actual_payments", ["loan_id", "payment_date"], unique=False)

    op.create_table(
        "scenario_actions",
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("action_type", postgresql.ENUM("close_early_full", "prepayment_partial", "reduce_payment", "skip", "add_income", "change_payment_date", name="scenario_action_type", create_type=False), nullable=False),
        sa.Column("loan_id", sa.UUID(), nullable=True),
        sa.Column("income_id", sa.UUID(), nullable=True),
        sa.Column("planned_payment_id", sa.UUID(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["income_id"], ["incomes.id"], name=op.f("fk_scenario_actions_income_id_incomes"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], name=op.f("fk_scenario_actions_loan_id_loans"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["planned_payment_id"], ["planned_payments.id"], name=op.f("fk_scenario_actions_planned_payment_id_planned_payments"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], name=op.f("fk_scenario_actions_scenario_id_scenarios"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario_actions")),
    )


def downgrade() -> None:
    op.drop_table("scenario_actions")
    op.drop_index("ix_actual_payments_loan_id_payment_date", table_name="actual_payments")
    op.drop_table("actual_payments")
    op.drop_index("ix_planned_payments_user_id_due_date", table_name="planned_payments")
    op.drop_index("ix_planned_payments_loan_id_due_date", table_name="planned_payments")
    op.drop_index("ix_planned_payments_income_id", table_name="planned_payments")
    op.drop_table("planned_payments")
    op.drop_table("loan_balances")
    op.drop_table("settings")
    op.drop_table("scenarios")
    op.drop_index("ix_loans_user_id_status", table_name="loans")
    op.drop_table("loans")
    op.drop_table("incomes")
    op.drop_index("ix_audit_log_entity_type_entity_id_changed_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("users")

    # Drop all enum types
    for name in ENUM_TYPES:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
