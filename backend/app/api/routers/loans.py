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
from app.services import loan_service

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
    return [LoanResponse.from_orm_model(ln) for ln in loans]


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    loan = await loan_service.get_loan(session, current_user.id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")
    return LoanResponse.from_orm_model(loan)


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
