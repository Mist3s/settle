"""Domain models package — re-exports all ORM models and Base.metadata.

Importing this module ensures all models are registered with the
declarative Base, which is required for Alembic autogeneration.
"""

from app.domain.models.audit import AuditLog
from app.domain.models.balance import LoanBalance
from app.domain.models.base import Base
from app.domain.models.income import Income
from app.domain.models.loan import Loan
from app.domain.models.payment import ActualPayment, PlannedPayment
from app.domain.models.scenario import Scenario, ScenarioAction
from app.domain.models.settings import Setting
from app.domain.models.user import User

__all__ = [
    "Base",
    "User",
    "Loan",
    "LoanBalance",
    "Income",
    "PlannedPayment",
    "ActualPayment",
    "Scenario",
    "ScenarioAction",
    "Setting",
    "AuditLog",
]
