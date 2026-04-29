"""CLI entry point: template, import, export.

Usage::

    python -m app.cli template [--with-examples] [--output PATH]
    python -m app.cli import --file PATH --user EMAIL --dry-run
    python -m app.cli import --file PATH --user EMAIL --commit
    python -m app.cli export --user EMAIL [--since DATE] [--output PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.domain.models.user import User
from app.services.export_service import export_to_xlsx
from app.services.import_ import CommitResult, run_dry_run
from app.services.template_service import generate_template

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _resolve_user(session: AsyncSession, email: str) -> uuid.UUID:
    """Look up user by email, abort if not found."""
    stmt = select(User.id).where(User.email == email, User.is_deleted.is_(False))
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        print(f"Ошибка: пользователь с email '{email}' не найден.", file=sys.stderr)  # noqa: RUF001
        sys.exit(1)
    return row


def _write_output(data: bytes, output: str | None) -> None:
    """Write *data* to *output* file or stdout."""
    if output:
        Path(output).write_bytes(data)
        print(f"Записано в {output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(data)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def _cmd_template(args: argparse.Namespace) -> None:
    data = generate_template(with_examples=args.with_examples)
    _write_output(data, args.output)


async def _cmd_import(args: argparse.Namespace) -> None:
    file_bytes = Path(args.file).read_bytes()

    async with async_session_factory() as session:
        user_id = await _resolve_user(session, args.user)
        report = await run_dry_run(session, user_id, file_bytes)

        if args.dry_run:
            print(report.model_dump_json(indent=2))
            return

        # --commit: dry-run succeeded, check for errors before committing.
        if report.has_errors:
            print(report.model_dump_json(indent=2))
            print(
                "\nИмпорт содержит ошибки, коммит невозможен.",  # noqa: RUF001
                file=sys.stderr,
            )
            sys.exit(1)

        # Re-use the parsed data via commit_import (from orchestrator).
        from app.services.import_ import commit_import

        result: CommitResult = await commit_import(
            session, user_id, report.import_id,
        )
        await session.commit()

        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


async def _cmd_export(args: argparse.Namespace) -> None:
    since: date | None = None
    if args.since:
        since = date.fromisoformat(args.since)

    async with async_session_factory() as session:
        user_id = await _resolve_user(session, args.user)
        data = await export_to_xlsx(session, user_id, since=since)

    _write_output(data, args.output)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Settle CLI: шаблон, импорт, экспорт XLSX.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- template --
    tpl = sub.add_parser("template", help="Сгенерировать XLSX-шаблон")
    tpl.add_argument("--with-examples", action="store_true", default=False,
                     help="Добавить пример-строки на каждый лист")
    tpl.add_argument("--output", type=str, default=None,
                     help="Путь к файлу (по умолчанию stdout)")

    # -- import --
    imp = sub.add_parser("import", help="Импорт из XLSX")
    imp.add_argument("--file", required=True, help="Путь к XLSX-файлу")
    imp.add_argument("--user", required=True, help="Email пользователя")
    mode = imp.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", default=False,
                      help="Только проверка (без записи)")
    mode.add_argument("--commit", action="store_true", default=False,
                      help="Проверка + запись в БД")

    # -- export --
    exp = sub.add_parser("export", help="Экспорт в XLSX")
    exp.add_argument("--user", required=True, help="Email пользователя")
    exp.add_argument("--since", type=str, default=None,
                     help="Фильтр по дате (ISO, например 2026-01-01)")
    exp.add_argument("--output", type=str, default=None,
                     help="Путь к файлу (по умолчанию stdout)")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_DISPATCH = {
    "template": _cmd_template,
    "import": _cmd_import,
    "export": _cmd_export,
}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    coro = _DISPATCH[args.command](args)
    asyncio.run(coro)


if __name__ == "__main__":
    main()
