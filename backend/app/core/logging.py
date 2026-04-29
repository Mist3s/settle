"""Structlog configuration — JSON output with request_id and sensitive data filtering."""

import logging
import re
import sys
from collections.abc import Mapping
from typing import Any

import structlog

from app.core.config import settings

# Keys whose values must be fully redacted in log output.
_REDACTED_KEYS = frozenset({
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
    "jwt_private_key",
    "jwt_private_key_path",
})

_REDACTED = "***"

# Pattern: keep only last 4 chars of a contract number, mask the rest.
_CONTRACT_RE = re.compile(r"^(.+?)(\d{4})$")


def _mask_contract_number(value: str) -> str:
    """Mask contract number, keeping only last 4 digits visible.

    Examples:
        "1234567890" -> "******7890"
        "ABC-12345678" -> "********5678"
    """
    m = _CONTRACT_RE.match(value)
    if m:
        prefix_len = len(m.group(1))
        return "*" * prefix_len + m.group(2)
    return value


def _sanitize_value(key: str, value: Any) -> Any:
    """Redact a single key-value pair if the key is sensitive."""
    key_lower = key.lower()

    if key_lower in _REDACTED_KEYS:
        return _REDACTED

    if key_lower == "contract_number" and isinstance(value, str) and len(value) > 4:
        return _mask_contract_number(value)

    return value


def _sanitize_event_dict(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all sensitive values in a log event dict."""
    sanitized: dict[str, Any] = {}
    for k, v in event_dict.items():
        if isinstance(v, Mapping):
            sanitized[k] = _sanitize_event_dict(dict(v))
        else:
            sanitized[k] = _sanitize_value(k, v)
    return sanitized


def filter_sensitive_data(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that filters sensitive data from log events.

    Implements §12.4 of architecture:
    - Redacts passwords, tokens, refresh-tokens
    - Masks contract numbers (shows only last 4 digits)
    """
    return _sanitize_event_dict(event_dict)


def setup_logging() -> None:
    """Configure structlog for JSON structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            filter_sensitive_data,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route standard library logging through structlog
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    ))
    root_logger.handlers = [handler]

    # Quieten noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )
