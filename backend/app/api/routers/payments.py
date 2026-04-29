"""Payments REST router — thin HTTP layer delegating to payment_service."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.domain.models.user import User
from app.domain.schemas.payment import (
    ActualPaymentCreate,
    ActualPaymentResponse,
    PlannedPaymentResponse,
    PlannedPaymentUpdate,
)
from app.services import payment_service

router = APIRouter(prefix="/api/payments", tags=["payments"])


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


# --- Planned ---

@router.get("/planned", response_model=list[PlannedPaymentResponse])
async def list_planned_payments(
    loan_id: UUID | None = Query(None),
    income_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[PlannedPaymentResponse]:
    payments = await payment_service.list_planned(
        session, current_user.id,
        loan_id=loan_id, income_id=income_id,
    )
    return [PlannedPaymentResponse.from_orm_model(p) for p in payments]


@router.get("/planned/{payment_id}", response_model=PlannedPaymentResponse)
async def get_planned_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PlannedPaymentResponse:
    payment = await payment_service.get_planned(
        session, current_user.id, payment_id,
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Плановый платёж не найден")
    return PlannedPaymentResponse.from_orm_model(payment)


@router.patch("/planned/{payment_id}", response_model=PlannedPaymentResponse)
async def update_planned_payment(
    payment_id: UUID,
    body: PlannedPaymentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PlannedPaymentResponse:
    update_data: dict = {}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k in ("amount", "principal_part", "interest_part"):
            v = _to_decimal(v, k)
        update_data[k] = v
    payment = await payment_service.update_planned(
        session, current_user.id, payment_id, **update_data,
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Плановый платёж не найден")
    await session.commit()
    return PlannedPaymentResponse.from_orm_model(payment)


# --- Actual ---

@router.post(
    "/actual",
    response_model=ActualPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_actual_payment(
    body: ActualPaymentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ActualPaymentResponse:
    payment = await payment_service.create_actual(
        session,
        current_user.id,
        loan_id=body.loan_id,
        planned_payment_id=body.planned_payment_id,
        amount=_to_decimal(body.amount, "amount") or Decimal(0),
        principal_part=_to_decimal(body.principal_part, "principal_part"),
        interest_part=_to_decimal(body.interest_part, "interest_part"),
        payment_date=body.payment_date,
        payment_type=body.payment_type,
        notes=body.notes,
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Кредит не найден")
    await session.commit()
    return ActualPaymentResponse.from_orm_model(payment)


@router.get("/actual", response_model=list[ActualPaymentResponse])
async def list_actual_payments(
    loan_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ActualPaymentResponse]:
    payments = await payment_service.list_actual(
        session, current_user.id, loan_id=loan_id,
    )
    return [ActualPaymentResponse.from_orm_model(p) for p in payments]


@router.delete("/actual/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_actual_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    payment = await payment_service.delete_actual(
        session, current_user.id, payment_id,
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Фактический платёж не найден")
    await session.commit()
