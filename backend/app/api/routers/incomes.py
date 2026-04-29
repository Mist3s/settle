"""Incomes REST router — thin HTTP layer delegating to income_service."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.domain.models.user import User
from app.domain.schemas.income import IncomeCreate, IncomeResponse, IncomeUpdate
from app.services import income_service

router = APIRouter(prefix="/api/incomes", tags=["incomes"])


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


@router.get("", response_model=list[IncomeResponse])
async def list_incomes(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[IncomeResponse]:
    incomes = await income_service.list_incomes(session, current_user.id)
    return [IncomeResponse.from_orm_model(i) for i in incomes]


@router.post("", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
async def create_income(
    body: IncomeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IncomeResponse:
    income = await income_service.create_income(
        session, current_user.id,
        code=body.code,
        expected_date=body.expected_date,
        amount=_to_decimal(body.amount, "amount") or Decimal(0),
        name=body.name,
        status=body.status,
        notes=body.notes,
    )
    await session.commit()
    return IncomeResponse.from_orm_model(income)


@router.patch("/{income_id}", response_model=IncomeResponse)
async def update_income(
    income_id: UUID,
    body: IncomeUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IncomeResponse:
    update_data: dict = {}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "amount":
            v = _to_decimal(v, k)
        update_data[k] = v
    income = await income_service.update_income(
        session, current_user.id, income_id, **update_data,
    )
    if income is None:
        raise HTTPException(status_code=404, detail="Поступление не найдено")
    await session.commit()
    return IncomeResponse.from_orm_model(income)


@router.post("/{income_id}/receive", response_model=IncomeResponse)
async def receive_income(
    income_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IncomeResponse:
    income = await income_service.receive_income(
        session, current_user.id, income_id,
    )
    if income is None:
        raise HTTPException(status_code=404, detail="Поступление не найдено")
    await session.commit()
    return IncomeResponse.from_orm_model(income)


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(
    income_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    income = await income_service.delete_income(
        session, current_user.id, income_id,
    )
    if income is None:
        raise HTTPException(status_code=404, detail="Поступление не найдено")
    await session.commit()
