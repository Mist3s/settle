"""PlannedPayment and ActualPayment repositories."""

from app.domain.models.payment import ActualPayment, PlannedPayment
from app.repositories.base import Repository


class PlannedPaymentRepository(Repository[PlannedPayment]):
    model = PlannedPayment


class ActualPaymentRepository(Repository[ActualPayment]):
    model = ActualPayment
