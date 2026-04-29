"""Import/export REST router — thin HTTP layer.

Endpoints:
  POST /api/import/excel           — multipart XLSX upload → dry-run report
  POST /api/import/excel/commit    — commit a dry-run by import_id
  GET  /api/import/template        — download empty/example XLSX template
  GET  /api/export/excel           — download full data export as XLSX
"""

from __future__ import annotations

import dataclasses
from datetime import date
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.domain.models.user import User
from app.domain.schemas.import_report import DryRunReport
from app.services.export_service import export_to_xlsx
from app.services.import_ import (
    ImportExpiredError,
    ImportNotFoundError,
    commit_import,
    run_dry_run,
)
from app.services.template_service import generate_template

log = structlog.get_logger()

router = APIRouter(tags=["import/export"])

# MIME for Office Open XML spreadsheets.
_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---------------------------------------------------------------------------
# Request schemas (must be before endpoint definitions)
# ---------------------------------------------------------------------------


class _CommitRequest(BaseModel):
    """Body for the commit endpoint."""

    model_config = ConfigDict(extra="forbid")
    import_id: UUID


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


@router.post("/api/import/excel", response_model=DryRunReport)
async def upload_excel(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DryRunReport:
    """Upload XLSX and run a dry-run import (parse → validate → diff)."""
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Файл пуст",
        )

    log.info(
        "import_dry_run_start",
        user_id=str(current_user.id),
        filename=file.filename,
        size=len(contents),
    )

    report = await run_dry_run(session, current_user.id, contents)
    return report


@router.post("/api/import/excel/commit")
async def commit_excel(
    body: _CommitRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Commit a previously uploaded dry-run import."""
    log.info(
        "import_commit_start",
        user_id=str(current_user.id),
        import_id=str(body.import_id),
    )

    try:
        result = await commit_import(session, current_user.id, body.import_id)
    except ImportExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc
    except ImportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await session.commit()
    return dataclasses.asdict(result)


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


@router.get("/api/import/template")
async def download_template(
    with_examples: bool = Query(default=False),
    _current_user: User = Depends(get_current_user),
) -> Response:
    """Download an XLSX import template (optionally with example rows)."""
    xlsx_bytes = generate_template(with_examples=with_examples)
    filename = "settle_template.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.get("/api/export/excel")
async def export_excel(
    since: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export all user data as XLSX, optionally filtered by date."""
    xlsx_bytes = await export_to_xlsx(session, current_user.id, since=since)
    filename = "settle_export.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
