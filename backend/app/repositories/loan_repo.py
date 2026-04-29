"""Loan repository."""

from app.domain.models.loan import Loan
from app.repositories.base import Repository


class LoanRepository(Repository[Loan]):
    model = Loan
