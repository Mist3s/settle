"""Income repository."""

from app.domain.models.income import Income
from app.repositories.base import Repository


class IncomeRepository(Repository[Income]):
    model = Income
