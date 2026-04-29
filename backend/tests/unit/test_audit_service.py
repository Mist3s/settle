"""Unit tests for audit_service serialization and record function."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.services.audit_service import _serialize_value


class TestSerializeValue:
    def test_uuid(self) -> None:
        uid = uuid.uuid4()
        assert _serialize_value(uid) == str(uid)

    def test_decimal(self) -> None:
        assert _serialize_value(Decimal("100.50")) == "100.50"

    def test_datetime(self) -> None:
        dt = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
        assert _serialize_value(dt) == dt.isoformat()

    def test_date(self) -> None:
        d = date(2026, 5, 1)
        assert _serialize_value(d) == "2026-05-01"

    def test_enum(self) -> None:
        from app.domain.enums import LoanStatus

        assert _serialize_value(LoanStatus.ACTIVE) == "active"

    def test_plain_value(self) -> None:
        assert _serialize_value("hello") == "hello"
        assert _serialize_value(42) == 42
        assert _serialize_value(None) is None
