"""Integration tests for import idempotency (architecture.md §11.4, §14.3).

Critical test: running the same XLSX twice yields an identical DB state.
Tests run against a real PostgreSQL instance (Docker Compose).
Each test gets its own transactional session that is rolled back.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.models.balance import LoanBalance
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import ActualPayment
from app.domain.models.user import User
from app.domain.schemas.import_dto import (
    ActualPaymentImportRow,
    BalanceImportRow,
    IncomeImportRow,
    LoanImportRow,
    ScheduleImportRow,
    SettingImportRow,
)
from app.services.export_service import export_to_xlsx
from app.services.import_.committer import commit_import
from app.services.import_.parser import ParsedData, parse_workbook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(session: AsyncSession) -> User:
    user = User(email="idem@settle.local", password_hash=hash_password("pw"))
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


def _full_parsed() -> ParsedData:
    """Reusable parsed dataset covering all entity types."""
    return ParsedData(
        settings=[SettingImportRow(key="usd_rub_rate", value="92.5")],
        loans=[
            LoanImportRow(
                code="IDEM_L1",
                creditor="Bank A",
                name="Loan 1",
                loan_type="credit",
                payment_method="annuity",
                original_amount=Decimal("200000"),
                interest_rate=Decimal("10"),
                opening_date=date(2025, 6, 1),
            ),
            LoanImportRow(
                code="IDEM_L2",
                creditor="Bank B",
                name="Loan 2",
                loan_type="installment",
                payment_method="installment",
                original_amount=Decimal("50000"),
                interest_rate=Decimal("0"),
                opening_date=date(2025, 7, 1),
            ),
        ],
        balances=[
            BalanceImportRow(
                loan_code="IDEM_L1",
                snapshot_date=date(2025, 8, 1),
                current_balance=Decimal("180000"),
            ),
            BalanceImportRow(
                loan_code="IDEM_L2",
                snapshot_date=date(2025, 8, 1),
                current_balance=Decimal("40000"),
            ),
        ],
        incomes=[
            IncomeImportRow(
                code="INC_IDEM",
                expected_date=date(2025, 9, 10),
                amount_rub=Decimal("60000"),
            ),
        ],
        schedule=[
            ScheduleImportRow(
                loan_code="IDEM_L1",
                due_date=date(2025, 9, 15),
                amount=Decimal("8000"),
            ),
        ],
        actual_payments=[
            ActualPaymentImportRow(
                loan_code="IDEM_L1",
                payment_date=date(2025, 8, 15),
                amount=Decimal("8000"),
                payment_type="regular",
            ),
        ],
    )


async def _snapshot_counts(
    session: AsyncSession,
    user_id,
) -> dict[str, int]:
    """Return entity counts keyed by type for quick comparison."""
    counts = {}
    for model, name in [
        (Loan, "loans"),
        (LoanBalance, "balances"),
        (Income, "incomes"),
        (ActualPayment, "actual_payments"),
    ]:
        q = select(func.count()).select_from(model)
        if hasattr(model, "user_id"):
            q = q.where(model.user_id == user_id)
        counts[name] = (await session.execute(q)).scalar_one()
    return counts


def _normalize_export(xlsx_bytes: bytes) -> dict[str, list[dict]]:
    """Parse export XLSX back to dicts, sorted by business keys for comparison.

    Strips timestamps and internal IDs so only business-meaningful data
    is compared.
    """
    parsed, errors, _ = parse_workbook(xlsx_bytes)
    assert not errors, f"Export re-parse errors: {errors}"

    result: dict[str, list[dict]] = {}

    result["settings"] = sorted(
        [r.model_dump() for r in parsed.settings],
        key=lambda r: r["key"],
    )
    result["loans"] = sorted(
        [r.model_dump() for r in parsed.loans],
        key=lambda r: r["code"],
    )
    result["balances"] = sorted(
        [r.model_dump() for r in parsed.balances],
        key=lambda r: (r["loan_code"], str(r["snapshot_date"])),
    )
    result["incomes"] = sorted(
        [r.model_dump() for r in parsed.incomes],
        key=lambda r: r["code"],
    )
    result["schedule"] = sorted(
        [r.model_dump() for r in parsed.schedule],
        key=lambda r: (r["loan_code"], str(r["due_date"])),
    )
    result["actual_payments"] = sorted(
        [r.model_dump() for r in parsed.actual_payments],
        key=lambda r: (r["loan_code"], str(r["payment_date"]), str(r["amount"])),
    )
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_double_import_identical_db(db_session: AsyncSession) -> None:
    """Import the same data twice → DB state identical after both runs.

    This is a critical test from architecture.md §14.3:
    «Идемпотентность импорта: прогон одного и того же Excel дважды
    даёт идентичную БД.»
    """
    user = await _create_user(db_session)
    parsed = _full_parsed()

    # First import.
    r1 = await commit_import(db_session, user.id, parsed)
    assert r1.loans_created == 2

    export_after_first = await export_to_xlsx(db_session, user.id)
    counts_after_first = await _snapshot_counts(db_session, user.id)

    # Second import — exact same data.
    r2 = await commit_import(db_session, user.id, parsed)

    # All creates must be zero; only updates.
    assert r2.loans_created == 0
    assert r2.balances_created == 0
    assert r2.incomes_created == 0
    assert r2.actual_payments_created == 0

    export_after_second = await export_to_xlsx(db_session, user.id)
    counts_after_second = await _snapshot_counts(db_session, user.id)

    # Entity counts must not change (no duplicates).
    assert counts_after_first == counts_after_second

    # Normalized exports must be identical.
    norm1 = _normalize_export(export_after_first)
    norm2 = _normalize_export(export_after_second)
    assert norm1 == norm2


@pytest.mark.asyncio()
async def test_roundtrip_export_import(db_session: AsyncSession) -> None:
    """Create data via import → export → re-import exported file → identical."""
    user = await _create_user(db_session)
    parsed = _full_parsed()

    # Phase 1: initial import.
    await commit_import(db_session, user.id, parsed)
    export_bytes = await export_to_xlsx(db_session, user.id)

    norm_before = _normalize_export(export_bytes)

    # Phase 2: re-import the exported file.
    re_parsed, errors, _ = parse_workbook(export_bytes)
    assert not errors, f"Re-parse errors: {errors}"

    r2 = await commit_import(db_session, user.id, re_parsed)

    # No new entities — everything matched by business key.
    assert r2.loans_created == 0
    assert r2.balances_created == 0
    assert r2.incomes_created == 0

    export_after = await export_to_xlsx(db_session, user.id)
    norm_after = _normalize_export(export_after)

    assert norm_before == norm_after


@pytest.mark.asyncio()
async def test_partial_update_single_row(db_session: AsyncSession) -> None:
    """Modified XLSX: one balance changed → only that record updates."""
    user = await _create_user(db_session)
    parsed = _full_parsed()

    await commit_import(db_session, user.id, parsed)

    # Capture loan DB state before second import.
    loans_before = (
        await db_session.execute(
            select(Loan.code, Loan.creditor).where(Loan.user_id == user.id)
            .order_by(Loan.code),
        )
    ).all()

    # Second import: change ONLY IDEM_L1 balance.
    modified = _full_parsed()
    modified.balances[0] = BalanceImportRow(
        loan_code="IDEM_L1",
        snapshot_date=date(2025, 8, 1),
        current_balance=Decimal("170000"),  # was 180000
    )

    r2 = await commit_import(db_session, user.id, modified)

    # IDEM_L1 balance should be updated, IDEM_L2 balance unchanged.
    assert r2.balances_updated >= 1

    # Verify IDEM_L1 balance actually changed.
    l1 = (
        await db_session.execute(
            select(Loan).where(Loan.code == "IDEM_L1", Loan.user_id == user.id),
        )
    ).scalar_one()
    bal = (
        await db_session.execute(
            select(LoanBalance).where(
                LoanBalance.loan_id == l1.id,
                LoanBalance.snapshot_date == date(2025, 8, 1),
            ),
        )
    ).scalar_one()
    assert bal.current_balance == Decimal("170000")

    # Verify IDEM_L2 balance is untouched.
    l2 = (
        await db_session.execute(
            select(Loan).where(Loan.code == "IDEM_L2", Loan.user_id == user.id),
        )
    ).scalar_one()
    bal2 = (
        await db_session.execute(
            select(LoanBalance).where(
                LoanBalance.loan_id == l2.id,
                LoanBalance.snapshot_date == date(2025, 8, 1),
            ),
        )
    ).scalar_one()
    assert bal2.current_balance == Decimal("40000")  # unchanged

    # Loans themselves should be identical.
    loans_after = (
        await db_session.execute(
            select(Loan.code, Loan.creditor).where(Loan.user_id == user.id)
            .order_by(Loan.code),
        )
    ).all()
    assert loans_before == loans_after

    # No new entities created (no duplicates).
    counts = await _snapshot_counts(db_session, user.id)
    assert counts["loans"] == 2
    assert counts["balances"] == 2
