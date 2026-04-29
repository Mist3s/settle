"""Loans REST router — thin HTTP layer delegating to loan_service."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.domain.enums import LoanStatus, LoanType
from app.domain.models.user import User
from app.domain.schemas.balance import BalanceCreate, BalanceResponse
from app.domain.schemas.loan import LoanCreate, LoanResponse, LoanUpdate
from app.domain.schemas.schedule import ScheduleEntryResponse
from app.services import balance_service, loan_service, schedule_service

router = APIRouter(prefix="/api/loans", tags=["loans"])


def _to_decimal(value: str | None, field_name: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Некорректное числовое значение: {field_name}",
        ) from exc


@router.get("", response_model=list[LoanResponse])
async def list_loans(
    loan_status: LoanStatus | None = Query(None, alias="status"),
    loan_type: LoanType | None = Query(None, alias="type"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[LoanResponse]:
    loans = await loan_service.list_loans(
        session, current_user.id,
        status=loan_status, loan_type=loan_type,
    )
    result = []
    for ln in loans:
        resp = LoanResponse.from_orm_model(ln)
        latest = await balance_service.get_latest(session, ln.id)
        if latest is not None:
            resp.current_balance = str(latest.current_balance)
            resp.balance_date = latest.snapshot_date
        result.append(resp)
    return result


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    loan = await loan_service.get_loan(session, current_user.id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")
    resp = LoanResponse.from_orm_model(loan)
    latest = await balance_service.get_latest(session, loan_id)
    if latest is not None:
        resp.current_balance = str(latest.current_balance)
        resp.balance_date = latest.snapshot_date
    return resp


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    body: LoanCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    loan = await loan_service.create_loan(
        session,
        current_user.id,
        code=body.code,
        creditor=body.creditor,
        name=body.name,
        loan_type=body.loan_type,
        payment_method=body.payment_method,
        original_amount=_to_decimal(body.original_amount, "original_amount"),
        interest_rate=_to_decimal(body.interest_rate, "interest_rate") or Decimal(0),
        opening_date=body.opening_date,
        closing_date=body.closing_date,
        prepayment_strategy=body.prepayment_strategy,
        priority=body.priority,
        status=body.status,
        contract_number=body.contract_number,
        notes=body.notes,
        late_fee_rate=_to_decimal(body.late_fee_rate, "late_fee_rate"),
        months_remaining=body.months_remaining,
        payment_day=body.payment_day,
    )
    await session.commit()
    return LoanResponse.from_orm_model(loan)


@router.patch("/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: UUID,
    body: LoanUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    update_data: dict = {}
    for field_name, value in body.model_dump(exclude_unset=True).items():
        if field_name in ("original_amount", "interest_rate", "late_fee_rate"):
            value = _to_decimal(value, field_name)
        update_data[field_name] = value

    loan = await loan_service.update_loan(
        session, current_user.id, loan_id, **update_data,
    )
    if loan is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")
    await session.commit()
    return LoanResponse.from_orm_model(loan)


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    loan = await loan_service.delete_loan(session, current_user.id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")
    await session.commit()


@router.post(
    "/{loan_id}/balance",
    response_model=BalanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_balance(
    loan_id: UUID,
    body: BalanceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BalanceResponse:
    balance = await loan_service.create_balance(
        session,
        current_user.id,
        loan_id,
        amount=_to_decimal(body.amount, "amount") or Decimal(0),
        principal_balance=_to_decimal(body.principal_balance, "principal_balance"),
        snapshot_date=body.snapshot_date,
        source=body.source,
        notes=body.notes,
    )
    if balance is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")
    await session.commit()
    return BalanceResponse.from_orm_model(balance)


# ------------------------------------------------------------------
# Schedule endpoints (Stage 5: financial engine)
# ------------------------------------------------------------------


def _schedule_entry_to_response(
    entry: schedule_service.ScheduleEntry,
) -> ScheduleEntryResponse:
    return ScheduleEntryResponse(
        due_date=entry.due_date,
        amount=str(entry.amount),
        principal_part=str(entry.principal_part),
        interest_part=str(entry.interest_part),
        balance_after=str(entry.balance_after),
    )


@router.get("/{loan_id}/schedule", response_model=list[ScheduleEntryResponse])
async def get_schedule(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ScheduleEntryResponse]:
    """Generate an annuity schedule from current loan parameters and latest balance."""
    loan = await loan_service.get_loan(session, current_user.id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")

    latest = await balance_service.get_latest(session, loan_id)
    if latest is None:
        raise HTTPException(
            status_code=422,
            detail="Нет снимка остатка — невозможно построить график",
        )

    months = loan.months_remaining
    if months is None or months <= 0:
        return []

    payment_day = loan.payment_day or latest.snapshot_date.day

    entries = schedule_service.generate_schedule(
        principal=latest.principal_balance,
        annual_rate=loan.interest_rate,
        months_remaining=months,
        start_date=latest.snapshot_date,
        payment_day=payment_day,
    )
    return [_schedule_entry_to_response(e) for e in entries]


@router.post(
    "/{loan_id}/recalc-schedule",
    response_model=list[ScheduleEntryResponse],
)
async def recalc_schedule(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ScheduleEntryResponse]:
    """Force-recalculate schedule from current balance and loan params.

    This is a read-only preview — does not modify planned_payments.
    """
    loan = await loan_service.get_loan(session, current_user.id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")

    latest = await balance_service.get_latest(session, loan_id)
    if latest is None:
        raise HTTPException(
            status_code=422,
            detail="Нет снимка остатка — невозможно пересчитать график",
        )

    months = loan.months_remaining
    if months is None or months <= 0:
        return []

    payment_day = loan.payment_day or latest.snapshot_date.day

    entries = schedule_service.generate_schedule(
        principal=latest.principal_balance,
        annual_rate=loan.interest_rate,
        months_remaining=months,
        start_date=latest.snapshot_date,
        payment_day=payment_day,
    )
    return [_schedule_entry_to_response(e) for e in entries]

