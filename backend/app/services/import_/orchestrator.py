"""Two-phase import orchestration: dry-run → commit.

run_dry_run   — phase 1: parse XLSX, validate, diff against DB, store report.
commit_import — phase 2: retrieve stored report, commit changes into DB.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas.import_report import DryRunReport
from app.services.import_.committer import commit_import as _do_commit
from app.services.import_.committer_core import CommitResult
from app.services.import_.cross_validator import cross_validate
from app.services.import_.diff import build_diff
from app.services.import_.parser import ParsedData, parse_workbook
from app.services.import_.storage import DryRunStore

# TTL for dry-run reports (30 min).
_DRY_RUN_TTL_SECONDS = 30 * 60

# Module-level singleton — sufficient for single-user app (architecture.md).
_store = DryRunStore()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ImportNotFoundError(Exception):
    """Raised when import_id is not found in the dry-run store."""


class ImportExpiredError(Exception):
    """Raised when import_id existed but its TTL has elapsed."""


# ---------------------------------------------------------------------------
# Phase 1 — dry run
# ---------------------------------------------------------------------------

async def run_dry_run(
    session: AsyncSession,
    user_id: uuid.UUID,
    file_bytes: bytes,
) -> DryRunReport:
    """Parse *file_bytes*, validate, diff against DB, and store the result.

    Returns a :class:`DryRunReport` with ``import_id`` that can be passed
    to :func:`commit_import` within the TTL window (30 min).
    """
    parsed, parse_errors, parse_warnings = parse_workbook(file_bytes)

    cross_errors = cross_validate(parsed) if not parse_errors else []

    all_errors = parse_errors + cross_errors

    if all_errors:
        return DryRunReport(
            import_id=uuid.uuid4(),
            expires_at=datetime.now(tz=UTC) + timedelta(seconds=_DRY_RUN_TTL_SECONDS),
            errors=all_errors,
            warnings=parse_warnings,
        )

    report = await build_diff(session, user_id, parsed)
    report.warnings.extend(parse_warnings)

    # Store (parsed_data, report) so commit_import can retrieve it later.
    _store.put(_StoredImport(parsed=parsed, report=report), key=report.import_id)

    return report


# ---------------------------------------------------------------------------
# Phase 2 — commit
# ---------------------------------------------------------------------------

async def commit_import(
    session: AsyncSession,
    user_id: uuid.UUID,
    import_id: uuid.UUID,
) -> CommitResult:
    """Commit a previously dry-run'd import into the database.

    Raises :exc:`ImportExpiredError` if *import_id* has expired or was
    never stored, :exc:`ImportNotFoundError` if stored data is corrupt.
    """
    entry = _store.get(import_id)
    if entry is None:
        raise ImportExpiredError(
            f"Импорт {import_id} не найден или истёк (TTL 30 мин)",
        )

    if not isinstance(entry, _StoredImport):
        raise ImportNotFoundError(f"Некорректные данные для {import_id}")

    return await _do_commit(session, user_id, entry.parsed)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

class _StoredImport:
    """Payload kept in :data:`_store` between dry-run and commit."""

    __slots__ = ("parsed", "report")

    def __init__(self, parsed: ParsedData, report: DryRunReport) -> None:
        self.parsed = parsed
        self.report = report
