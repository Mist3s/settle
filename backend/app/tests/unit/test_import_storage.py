"""Unit tests for DryRunStore (in-memory TTL storage)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from app.services.import_.storage import DryRunStore


class TestDryRunStore:
    """Tests for put, get, expiry, and lazy GC."""

    def test_put_and_get_returns_payload(self) -> None:
        store = DryRunStore(ttl=60)
        payload = {"loans": 3, "errors": []}
        key = store.put(payload)

        assert isinstance(key, uuid.UUID)
        assert store.get(key) is payload

    def test_get_missing_key_returns_none(self) -> None:
        store = DryRunStore(ttl=60)
        assert store.get(uuid.uuid4()) is None

    def test_get_expired_entry_returns_none(self) -> None:
        store = DryRunStore(ttl=10)
        key = store.put({"data": 1})

        # Advance monotonic clock past TTL.
        with patch("app.services.import_.storage.time") as mock_time:
            # First call: time.monotonic() inside put() already happened with real time.
            # We only need expire_old() to see a future timestamp.
            mock_time.monotonic.return_value = 1e12  # far future
            result = store.get(key)

        assert result is None

    def test_expire_old_removes_stale_entries(self) -> None:
        store = DryRunStore(ttl=5)
        store.put("a")
        store.put("b")
        assert len(store) == 2

        with patch("app.services.import_.storage.time") as mock_time:
            mock_time.monotonic.return_value = 1e12
            store.expire_old()

        assert len(store) == 0

    def test_lazy_gc_on_get_keeps_valid_entries(self) -> None:
        """get() must GC expired entries but keep fresh ones."""
        store = DryRunStore(ttl=100)
        key_old = store.put("old")
        key_new = store.put("new")

        # Expire only key_old by manipulating its internal expires_at.
        store._data[key_old].expires_at = 0.0

        # get(key_new) triggers expire_old → key_old is purged.
        assert store.get(key_new) == "new"
        assert store.get(key_old) is None
        assert len(store) == 1

    def test_put_generates_unique_keys(self) -> None:
        store = DryRunStore(ttl=60)
        keys = {store.put(i) for i in range(20)}
        assert len(keys) == 20
