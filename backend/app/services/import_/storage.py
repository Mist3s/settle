"""In-memory dry-run result store with TTL and lazy GC."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

# TTL in seconds (30 minutes).
_DEFAULT_TTL: int = 30 * 60


@dataclass(slots=True)
class _Entry:
    payload: Any
    expires_at: float


class DryRunStore:
    """Thread-safe-enough store for a single-user app.

    put()  → stores payload under a new UUID, returns the key.
    get()  → returns payload or None if expired / missing; runs lazy GC.
    expire_old() → removes all expired entries.
    """

    def __init__(self, ttl: int = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._data: dict[uuid.UUID, _Entry] = {}

    # -- public API ----------------------------------------------------------

    def put(self, payload: Any, *, key: uuid.UUID | None = None) -> uuid.UUID:
        """Store *payload* and return the UUID key.

        If *key* is not provided a fresh one is generated.
        """
        if key is None:
            key = uuid.uuid4()
        self._data[key] = _Entry(
            payload=payload,
            expires_at=time.monotonic() + self._ttl,
        )
        return key

    def get(self, import_id: uuid.UUID) -> Any | None:
        """Return stored payload or ``None`` if missing / expired.

        Triggers lazy GC as a side-effect.
        """
        self.expire_old()
        entry = self._data.get(import_id)
        if entry is None:
            return None
        return entry.payload

    def expire_old(self) -> None:
        """Remove all entries whose TTL has elapsed."""
        now = time.monotonic()
        expired_keys = [k for k, v in self._data.items() if v.expires_at <= now]
        for k in expired_keys:
            del self._data[k]

    # -- helpers (testing) ---------------------------------------------------

    def __len__(self) -> int:
        return len(self._data)
