"""Pydantic schemas for the two-phase import dry-run report.

These models are produced by the diff stage (services/import_/diff.py)
and returned to the client from ``POST /api/import/excel``.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class ImportSeverity(StrEnum):
    """Severity level for import issues."""
    error = "error"
    warning = "warning"


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

class ImportError(BaseModel):
    """Validation or parsing error with sheet coordinates."""
    model_config = ConfigDict(extra="forbid")

    sheet: str
    row: int | None = None
    column: str | None = None
    message: str


class ImportWarning(BaseModel):
    """Non-blocking warning with sheet coordinates."""
    model_config = ConfigDict(extra="forbid")

    sheet: str
    row: int | None = None
    column: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

class EntityDiff(BaseModel):
    """Per-entity create/update breakdown."""
    model_config = ConfigDict(extra="forbid")

    to_create: int = 0
    to_update: int = 0


class ScheduleDiff(EntityDiff):
    """Schedule-specific diff that includes planned payments to cancel."""
    to_cancel_existing: int = 0


# ---------------------------------------------------------------------------
# Summary & Report
# ---------------------------------------------------------------------------

class DryRunSummary(BaseModel):
    """Aggregated counts across all entity types."""
    model_config = ConfigDict(extra="forbid")

    loans: EntityDiff = Field(default_factory=EntityDiff)
    balances: EntityDiff = Field(default_factory=EntityDiff)
    schedule: ScheduleDiff = Field(default_factory=ScheduleDiff)
    incomes: EntityDiff = Field(default_factory=EntityDiff)
    actual_payments: EntityDiff = Field(default_factory=EntityDiff)


class DryRunReport(BaseModel):
    """Full dry-run result returned to the client."""
    model_config = ConfigDict(extra="forbid")

    import_id: uuid.UUID
    expires_at: datetime
    summary: DryRunSummary = Field(default_factory=DryRunSummary)
    errors: list[ImportError] = Field(default_factory=list)
    warnings: list[ImportWarning] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
