"""Integration tests for Stage 2: domain model constraints and schema integrity.

Given: a clean DB with 001_initial_schema applied
When: inserting rows that violate constraints
Then: IntegrityError is raised with the expected constraint name
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import ClassVar

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import (
    BalanceSource,
    LoanStatus,
    LoanType,
    PaymentAccuracy,
    PaymentMethod,
    PaymentStatus,
    PrepaymentStrategy,
)
from app.domain.models import (
    AuditLog,
    Loan,
    LoanBalance,
    PlannedPayment,
    Scenario,
    ScenarioAction,
    Setting,
    User,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**overrides) -> User:
    defaults = {
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "password_hash": hash_password("test"),
    }
    defaults.update(overrides)
    return User(**defaults)


def _make_loan(user_id: uuid.UUID, **overrides) -> Loan:
    defaults = {
        "user_id": user_id,
        "code": f"LOAN-{uuid.uuid4().hex[:6]}",
        "creditor": "Test Bank",
        "name": "Test Loan",
        "loan_type": LoanType.CREDIT,
        "payment_method": PaymentMethod.ANNUITY,
        "interest_rate": Decimal("12.5000"),
        "status": LoanStatus.ACTIVE,
        "prepayment_strategy": PrepaymentStrategy.REDUCE_PAYMENT,
    }
    defaults.update(overrides)
    return Loan(**defaults)


# ---------------------------------------------------------------------------
# PG enum types exist
# ---------------------------------------------------------------------------

class TestEnumTypesExist:
    """Given: migration applied, When: querying pg_type, Then: all 12 enum types exist."""

    EXPECTED_ENUMS: ClassVar[set[str]] = {
        "loan_type", "loan_status", "payment_method", "payment_status",
        "payment_accuracy", "actual_payment_type", "income_status",
        "balance_source", "prepayment_strategy", "scenario_action_type",
        "scenario_status", "audit_action",
    }

    async def test_all_enum_types_present(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT typname FROM pg_type WHERE typtype = 'e' "
                "AND typname = ANY(:names)"
            ),
            {"names": list(self.EXPECTED_ENUMS)},
        )
        found = {row[0] for row in result.fetchall()}
        assert found == self.EXPECTED_ENUMS, f"Missing enums: {self.EXPECTED_ENUMS - found}"


# ---------------------------------------------------------------------------
# Table existence
# ---------------------------------------------------------------------------

class TestTablesExist:
    """Given: migration applied, When: querying information_schema, Then: all tables exist."""

    EXPECTED_TABLES: ClassVar[set[str]] = {
        "users", "loans", "loan_balances", "incomes",
        "planned_payments", "actual_payments", "scenarios",
        "scenario_actions", "settings", "audit_log",
    }

    async def test_all_tables_present(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:names)"
            ),
            {"names": list(self.EXPECTED_TABLES)},
        )
        found = {row[0] for row in result.fetchall()}
        assert found == self.EXPECTED_TABLES, f"Missing tables: {self.EXPECTED_TABLES - found}"


# ---------------------------------------------------------------------------
# CHECK constraints
# ---------------------------------------------------------------------------

class TestCheckConstraints:
    """Tests for CHECK constraints defined in models."""

    async def test_loan_negative_interest_rate_rejected(self, db_session: AsyncSession):
        """Given: interest_rate < 0, When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(user.id, interest_rate=Decimal("-1.0000"))
        db_session.add(loan)

        with pytest.raises(IntegrityError, match="positive_interest_rate"):
            await db_session.flush()

    async def test_loan_closing_before_opening_rejected(self, db_session: AsyncSession):
        """Given: closing_date < opening_date, When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(
            user.id,
            opening_date=date(2025, 6, 1),
            closing_date=date(2025, 1, 1),
        )
        db_session.add(loan)

        with pytest.raises(IntegrityError, match="closing_after_opening"):
            await db_session.flush()

    async def test_loan_balance_negative_principal_rejected(self, db_session: AsyncSession):
        """Given: principal_balance < 0, When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(user.id)
        db_session.add(loan)
        await db_session.flush()

        balance = LoanBalance(
            loan_id=loan.id,
            snapshot_date=date(2025, 1, 1),
            current_balance=Decimal("1000.00"),
            principal_balance=Decimal("-1.00"),
            accrued_interest=Decimal("0.00"),
            source=BalanceSource.MANUAL,
        )
        db_session.add(balance)

        with pytest.raises(IntegrityError, match="non_negative_principal"):
            await db_session.flush()

    async def test_planned_payment_zero_amount_rejected(self, db_session: AsyncSession):
        """Given: amount = 0, When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(user.id)
        db_session.add(loan)
        await db_session.flush()

        pp = PlannedPayment(
            user_id=user.id,
            loan_id=loan.id,
            due_date=date(2025, 2, 1),
            amount=Decimal("0.00"),
            status=PaymentStatus.PENDING,
            accuracy=PaymentAccuracy.ESTIMATE,
        )
        db_session.add(pp)

        with pytest.raises(IntegrityError, match="positive_amount"):
            await db_session.flush()


# ---------------------------------------------------------------------------
# Unique constraints
# ---------------------------------------------------------------------------

class TestUniqueConstraints:
    async def test_duplicate_loan_code_per_user_rejected(self, db_session: AsyncSession):
        """Given: two loans with same (user_id, code), When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        code = "DUPL-001"
        loan1 = _make_loan(user.id, code=code)
        loan2 = _make_loan(user.id, code=code)
        db_session.add_all([loan1, loan2])

        with pytest.raises(IntegrityError, match="uq_loans_user_id_code"):
            await db_session.flush()

    async def test_duplicate_balance_snapshot_rejected(self, db_session: AsyncSession):
        """Given: duplicate (loan_id, snapshot_date), When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(user.id)
        db_session.add(loan)
        await db_session.flush()

        snap_date = date(2025, 3, 1)
        common = {
            "loan_id": loan.id,
            "snapshot_date": snap_date,
            "current_balance": Decimal("5000.00"),
            "principal_balance": Decimal("4500.00"),
            "accrued_interest": Decimal("500.00"),
            "source": BalanceSource.MANUAL,
        }
        b1 = LoanBalance(**common)
        b2 = LoanBalance(**common)
        db_session.add_all([b1, b2])

        with pytest.raises(IntegrityError, match="uq_loan_balances_loan_id_snapshot_date"):
            await db_session.flush()

    async def test_duplicate_setting_key_per_user_rejected(self, db_session: AsyncSession):
        """Given: two settings with same (user_id, key), When: flush, Then: IntegrityError."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        s1 = Setting(user_id=user.id, key="theme", value="dark")
        s2 = Setting(user_id=user.id, key="theme", value="light")
        db_session.add_all([s1, s2])

        with pytest.raises(IntegrityError, match="uq_settings_user_id_key"):
            await db_session.flush()

    async def test_duplicate_user_email_rejected(self, db_session: AsyncSession):
        """Given: two users with same email, When: flush, Then: IntegrityError."""
        email = "unique-test@example.com"
        u1 = _make_user(email=email)
        u2 = _make_user(email=email)
        db_session.add_all([u1, u2])

        with pytest.raises(IntegrityError, match="uq_users_email"):
            await db_session.flush()


# ---------------------------------------------------------------------------
# FK constraints
# ---------------------------------------------------------------------------

class TestForeignKeyConstraints:
    async def test_loan_with_nonexistent_user_rejected(self, db_session: AsyncSession):
        """Given: loan.user_id points to non-existent user, When: flush, Then: IntegrityError."""
        loan = _make_loan(uuid.uuid4())
        db_session.add(loan)

        with pytest.raises(IntegrityError, match="fk_loans_user_id_users"):
            await db_session.flush()


# ---------------------------------------------------------------------------
# Soft delete columns
# ---------------------------------------------------------------------------

class TestSoftDeleteDefaults:
    async def test_user_created_with_is_deleted_false(self, db_session: AsyncSession):
        """Given: new user, When: flush, Then: is_deleted=False, deleted_at=None."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        assert user.is_deleted is False
        assert user.deleted_at is None

    async def test_loan_created_with_soft_delete_defaults(self, db_session: AsyncSession):
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(user.id)
        db_session.add(loan)
        await db_session.flush()
        await db_session.refresh(loan)

        assert loan.is_deleted is False
        assert loan.deleted_at is None


# ---------------------------------------------------------------------------
# Server defaults
# ---------------------------------------------------------------------------

class TestServerDefaults:
    async def test_loan_defaults(self, db_session: AsyncSession):
        """Given: loan with minimal fields, When: flush, Then: server defaults applied."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        loan = _make_loan(user.id)
        db_session.add(loan)
        await db_session.flush()
        await db_session.refresh(loan)

        assert loan.status == LoanStatus.ACTIVE
        assert loan.prepayment_strategy == PrepaymentStrategy.REDUCE_PAYMENT
        assert loan.interest_rate == Decimal("12.5000")
        assert loan.created_at is not None
        assert loan.updated_at is not None

    async def test_audit_log_changed_at_default(self, db_session: AsyncSession):
        """Given: audit log entry, When: flush, Then: changed_at auto-set."""
        entry = AuditLog(
            entity_type="test",
            entity_id=uuid.uuid4(),
            action="create",
        )
        db_session.add(entry)
        await db_session.flush()
        await db_session.refresh(entry)

        assert entry.changed_at is not None


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------

class TestCascadeDelete:
    async def test_scenario_actions_cascade_on_scenario_delete(self, db_session: AsyncSession):
        """Given: scenario with actions, When: delete scenario, Then: actions also deleted."""
        user = _make_user()
        db_session.add(user)
        await db_session.flush()

        scenario = Scenario(
            user_id=user.id,
            name="Test Scenario",
            base_date=date(2025, 1, 1),
        )
        db_session.add(scenario)
        await db_session.flush()

        action = ScenarioAction(
            scenario_id=scenario.id,
            action_type="skip",
            effective_date=date(2025, 2, 1),
        )
        db_session.add(action)
        await db_session.flush()

        action_id = action.id

        # Delete via raw SQL to test FK CASCADE (ORM delete would use python cascade)
        await db_session.execute(
            text("DELETE FROM scenarios WHERE id = :sid"),
            {"sid": scenario.id},
        )

        # Verify action is also gone
        result = await db_session.execute(
            text("SELECT id FROM scenario_actions WHERE id = :aid"),
            {"aid": action_id},
        )
        assert result.fetchone() is None
