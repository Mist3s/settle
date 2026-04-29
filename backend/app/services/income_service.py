"""Income service — business logic for income management."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, IncomeStatus
from app.domain.models.income import Income
from app.repositories.income_repo import IncomeRepository
from app.services import audit_service


async def list_incomes(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[Income]:
    repo = IncomeRepository(session)
    return await repo.list(filters={"user_id": user_id})


async def get_income(
    session: AsyncSession,
    user_id: uuid.UUID,
    income_id: uuid.UUID,
) -> Income | None:
    repo = IncomeRepository(session)
    income = await repo.get(income_id)
    if income is None or income.user_id != user_id:
        return None
    return income


async def create_income(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    code: str,
    expected_date,
    amount: Decimal,
    name: str | None = None,
    status: IncomeStatus = IncomeStatus.EXPECTED,
    notes: str | None = None,
) -> Income:
    repo = IncomeRepository(session)
    income = await repo.create(
        user_id=user_id,
        code=code,
        expected_date=expected_date,
        amount=amount,
        name=name,
        status=status,
        notes=notes,
    )
    await audit_service.record(
        session,
        entity_type="incomes",
        entity_id=income.id,
        action=AuditAction.CREATE,
        after_state=audit_service.model_to_dict(income),
        changed_by=user_id,
    )
    return income


async def update_income(
    session: AsyncSession,
    user_id: uuid.UUID,
    income_id: uuid.UUID,
    **kwargs,
) -> Income | None:
    repo = IncomeRepository(session)
    income = await repo.get(income_id)
    if income is None or income.user_id != user_id:
        return None
    before = audit_service.model_to_dict(income)
    if kwargs:
        await repo.update(income_id, **kwargs)
    after = audit_service.model_to_dict(income)
    await audit_service.record(
        session,
        entity_type="incomes",
        entity_id=income.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return income


async def receive_income(
    session: AsyncSession,
    user_id: uuid.UUID,
    income_id: uuid.UUID,
) -> Income | None:
    return await update_income(
        session, user_id, income_id,
        status=IncomeStatus.RECEIVED,
    )


async def delete_income(
    session: AsyncSession,
    user_id: uuid.UUID,
    income_id: uuid.UUID,
) -> Income | None:
    repo = IncomeRepository(session)
    income = await repo.get(income_id)
    if income is None or income.user_id != user_id:
        return None
    before = audit_service.model_to_dict(income)
    await repo.soft_delete(income_id)
    after = audit_service.model_to_dict(income)
    await audit_service.record(
        session,
        entity_type="incomes",
        entity_id=income.id,
        action=AuditAction.DELETE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return income
