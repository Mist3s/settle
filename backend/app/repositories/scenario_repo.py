"""Scenario and ScenarioAction repositories."""

import uuid

from sqlalchemy import select

from app.domain.models.scenario import Scenario, ScenarioAction
from app.repositories.base import Repository


class ScenarioRepository(Repository[Scenario]):
    model = Scenario


class ScenarioActionRepository(Repository[ScenarioAction]):
    model = ScenarioAction

    async def list_by_scenario(
        self, scenario_id: uuid.UUID
    ) -> list[ScenarioAction]:
        """Return all actions for a scenario, ordered by effective_date."""
        stmt = (
            select(ScenarioAction)
            .where(ScenarioAction.scenario_id == scenario_id)
            .order_by(ScenarioAction.effective_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
