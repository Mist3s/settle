"""Unit tests for structlog sensitive data filtering (§12.4)."""

import pytest

from app.core.logging import (
    _mask_contract_number,
    _sanitize_value,
    filter_sensitive_data,
)


class TestMaskContractNumber:
    def test_numeric_contract(self):
        assert _mask_contract_number("1234567890") == "******7890"

    def test_alphanumeric_contract(self):
        assert _mask_contract_number("ABC-12345678") == "********5678"

    def test_short_contract(self):
        # 4 chars — 0-char prefix + 4 last
        assert _mask_contract_number("1234") == "1234"

    def test_five_char_contract(self):
        assert _mask_contract_number("12345") == "*2345"


class TestSanitizeValue:
    @pytest.mark.parametrize("key", [
        "password", "Password", "PASSWORD",
        "token", "access_token", "refresh_token",
        "authorization", "secret",
        "jwt_private_key", "jwt_private_key_path",
    ])
    def test_redacted_keys(self, key: str):
        assert _sanitize_value(key, "super-secret-value") == "***"

    def test_password_hash_redacted(self):
        assert _sanitize_value("password_hash", "$argon2id$...") == "***"

    def test_contract_number_masked(self):
        assert _sanitize_value("contract_number", "1234567890") == "******7890"

    def test_short_contract_number_not_masked(self):
        # 4 chars or fewer — no masking
        assert _sanitize_value("contract_number", "1234") == "1234"

    def test_regular_key_not_touched(self):
        assert _sanitize_value("loan_code", "ALPHA_001") == "ALPHA_001"

    def test_amount_not_touched(self):
        assert _sanitize_value("amount", "12345.67") == "12345.67"


class TestFilterSensitiveData:
    def test_flat_event_dict(self):
        event = {
            "event": "login_attempt",
            "password": "my-secret",
            "email": "user@test.com",
        }
        result = filter_sensitive_data(None, "info", event)
        assert result["password"] == "***"
        assert result["email"] == "user@test.com"

    def test_nested_dict(self):
        event = {
            "event": "audit",
            "before_state": {
                "contract_number": "AB123456789012",
                "name": "Test Loan",
            },
        }
        result = filter_sensitive_data(None, "info", event)
        assert result["before_state"]["contract_number"] == "**********9012"
        assert result["before_state"]["name"] == "Test Loan"

    def test_preserves_non_sensitive_keys(self):
        event = {
            "event": "http_request",
            "path": "/api/loans",
            "method": "GET",
            "status_code": 200,
            "duration_ms": 42.5,
            "request_id": "abc-123",
        }
        result = filter_sensitive_data(None, "info", event)
        assert result == event

    def test_multiple_sensitive_keys(self):
        event = {
            "access_token": "eyJhb...",
            "refresh_token": "eyJhb...",
            "password": "secret",
            "user_id": "user-123",
        }
        result = filter_sensitive_data(None, "info", event)
        assert result["access_token"] == "***"
        assert result["refresh_token"] == "***"
        assert result["password"] == "***"
        assert result["user_id"] == "user-123"
