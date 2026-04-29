"""Integration tests for observability endpoints: health ready + Prometheus metrics."""

from httpx import AsyncClient


class TestHealthReady:
    async def test_health_ready_checks_db_and_migrations(self, client: AsyncClient):
        """Given: DB is up with migrations applied.
        When: GET /health/ready
        Then: 200 ok.
        """
        resp = await client.get("/api/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestMetricsEndpoint:
    async def test_metrics_returns_prometheus_format(self, client: AsyncClient):
        """Given: app is running with prometheus instrumentator.
        When: GET /metrics
        Then: 200 with Prometheus text format containing standard HTTP metrics.
        """
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        # Standard instrumentator metrics should be present
        assert "http_request_duration_seconds" in body or "http_requests_total" in body

    async def test_custom_metrics_registered(self, client: AsyncClient):
        """Given: custom metrics are declared.
        When: GET /metrics
        Then: custom metric names appear in output.
        """
        resp = await client.get("/metrics")
        body = resp.text
        assert "payments_planned_today" in body
        assert "forecast_compute_duration_seconds" in body
        # loan_balance_total may not have samples yet, but TYPE line should exist
        assert "loan_balance_total" in body


class TestRequestLogging:
    async def test_request_id_header_returned(self, client: AsyncClient):
        """Given: any request.
        When: calling any endpoint
        Then: X-Request-ID header is returned.
        """
        resp = await client.get("/api/health/live")
        assert "X-Request-ID" in resp.headers
        # Should be a valid UUID-like string
        assert len(resp.headers["X-Request-ID"]) >= 32
