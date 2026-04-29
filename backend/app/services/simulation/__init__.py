"""Simulation package — overlay engine for scenario forecasting.

Architecture §6: overlay applies actions in-memory, never writes to DB.
"""

from app.services.simulation.engine import build_forecast
from app.services.simulation.materializer import apply_scenario, archive_scenario

__all__ = ["apply_scenario", "archive_scenario", "build_forecast"]
