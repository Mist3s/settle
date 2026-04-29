"""Prometheus metrics setup — instrumentator + custom gauges/histograms.

Architecture §13.2:
- prometheus-fastapi-instrumentator on /metrics
- Custom: loan_balance_total, payments_planned_today, forecast_compute_duration_seconds
"""

from prometheus_client import Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# -- Custom metrics -----------------------------------------------------------

loan_balance_total = Gauge(
    "loan_balance_total",
    "Current outstanding balance per loan",
    ["loan_code"],
)

payments_planned_today = Gauge(
    "payments_planned_today",
    "Number of planned payments due today",
)

forecast_compute_duration_seconds = Histogram(
    "forecast_compute_duration_seconds",
    "Time to compute a forecast projection",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# -- Instrumentator instance --------------------------------------------------

instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    excluded_handlers=["/api/health/live", "/api/health/ready", "/metrics"],
    inprogress_name="settle_http_requests_in_progress",
    inprogress_labels=True,
)
