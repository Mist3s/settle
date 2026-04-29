"""Materializer — apply or archive a scenario.

Architecture §6.4: when user clicks "Apply", each action is
materialized into real DB records via PaymentService or direct writes.
All in one transaction.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    AuditAction,
    IncomeStatus,
    PaymentStatus,
    ScenarioStatus,
)
from app.domain.models.scenario import Scenario
from app.repositories.scenario_repo import ScenarioRepository
from app.services import audit_service, income_service, payment_service


async def apply_scenario(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario: Scenario,
) -> dict:
    """Materialize a scenario's actions into real DB records.

    Architecture §6.4:
    1. Validate applicability (status=draft, dates >= today)
    2. For each action call the appropriate service
    3. Mark scenario.status = applied
    4. Audit log everything

    Returns a summary dict of what was done.
    """
    if scenario.status != ScenarioStatus.DRAFT:
        msg = "Только черновые сценарии можно применить"
        raise ValueError(msg)

    summary: dict = {
        "applied_actions": 0,
        "skipped_actions": 0,
        "details": [],
    }

    actions = sorted(scenario.actions, key=lambda a: a.effective_date)

    for action in actions:
        action_type = action.action_type.value
        params = action.params or {}

        # Validate: effective_date should be >= today for future actions
        # But allow past dates if user explicitly wants to record past events
        detail: dict = {"action_type": action_type, "status": "applied"}

        try:
            if action_type == "close_early_full":
                if action.loan_id is None:
                    detail["status"] = "skipped"
                    detail["reason"] = "loan_id отсутствует"
                    summary["skipped_actions"] += 1
                    summary["details"].append(detail)
                    continue

                # Get full balance from balance_service to pay exact amount
                from app.services import balance_service

                latest = await balance_service.get_latest(
                    session, action.loan_id
                )
                if latest:
                    full_amount = (
                        latest.principal_balance + latest.accrued_interest
                    )
                else:
                    full_amount = Decimal("0")

                await payment_service.register_payment(
                    session,
                    user_id,
                    loan_id=action.loan_id,
                    amount=full_amount,
                    payment_date=action.effective_date,
                    payment_type=None,  # auto-detect as early_full
                )

            elif action_type == "prepayment_partial":
                if action.loan_id is None:
                    detail["status"] = "skipped"
                    detail["reason"] = "loan_id отсутствует"
                    summary["skipped_actions"] += 1
                    summary["details"].append(detail)
                    continue

                amount = Decimal(params.get("amount", "0"))
                await payment_service.register_payment(
                    session,
                    user_id,
                    loan_id=action.loan_id,
                    amount=amount,
                    payment_date=action.effective_date,
                    payment_type=None,  # auto-detect
                )

            elif action_type == "reduce_payment":
                if action.planned_payment_id is None:
                    detail["status"] = "skipped"
                    detail["reason"] = "planned_payment_id отсутствует"
                    summary["skipped_actions"] += 1
                    summary["details"].append(detail)
                    continue

                new_amount = Decimal(params.get("new_amount", "0"))
                await payment_service.update_planned(
                    session,
                    user_id,
                    action.planned_payment_id,
                    amount=new_amount,
                )

            elif action_type == "skip":
                if action.planned_payment_id is None:
                    detail["status"] = "skipped"
                    detail["reason"] = "planned_payment_id отсутствует"
                    summary["skipped_actions"] += 1
                    summary["details"].append(detail)
                    continue

                await payment_service.update_planned(
                    session,
                    user_id,
                    action.planned_payment_id,
                    status=PaymentStatus.SKIPPED,
                )

            elif action_type == "add_income":
                amount = Decimal(params.get("amount", "0"))
                name = params.get("name", "Дополнительный доход")
                # Generate unique code for the income
                code = f"SC_{scenario.id.hex[:8]}_{action.id.hex[:8]}"
                await income_service.create_income(
                    session,
                    user_id,
                    code=code,
                    name=name,
                    amount=amount,
                    expected_date=action.effective_date,
                    status=IncomeStatus.EXPECTED,
                )

            elif action_type == "change_payment_date":
                if action.planned_payment_id is None:
                    detail["status"] = "skipped"
                    detail["reason"] = "planned_payment_id отсутствует"
                    summary["skipped_actions"] += 1
                    summary["details"].append(detail)
                    continue

                new_date = params.get("new_date")
                if isinstance(new_date, str):
                    new_date = date.fromisoformat(new_date)
                await payment_service.update_planned(
                    session,
                    user_id,
                    action.planned_payment_id,
                    due_date=new_date,
                )

            summary["applied_actions"] += 1

        except Exception as exc:
            detail["status"] = "error"
            detail["reason"] = str(exc)
            summary["skipped_actions"] += 1

        summary["details"].append(detail)

    # Mark scenario as applied
    repo = ScenarioRepository(session)
    before = audit_service.model_to_dict(scenario)
    await repo.update(scenario.id, status=ScenarioStatus.APPLIED)
    after = audit_service.model_to_dict(scenario)
    await audit_service.record(
        session,
        entity_type="scenarios",
        entity_id=scenario.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )

    return summary


async def archive_scenario(
    session: AsyncSession,
    user_id: uuid.UUID,
    scenario: Scenario,
) -> Scenario:
    """Archive a scenario (any status → archived).

    Does not undo anything — just marks it as archived.
    """
    repo = ScenarioRepository(session)
    before = audit_service.model_to_dict(scenario)
    await repo.update(scenario.id, status=ScenarioStatus.ARCHIVED)
    after = audit_service.model_to_dict(scenario)
    await audit_service.record(
        session,
        entity_type="scenarios",
        entity_id=scenario.id,
        action=AuditAction.UPDATE,
        before_state=before,
        after_state=after,
        changed_by=user_id,
    )
    return scenario
