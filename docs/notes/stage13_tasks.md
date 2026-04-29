# Этап 13: Наблюдаемость, метрики, health checks

## Задачи

- [ ] 1. `core/logging.py` — добавить structlog processor для фильтрации чувствительных данных (§12.4)
- [ ] 2. `main.py` — HTTP request/response logging middleware с user_id, path, method, status_code, duration_ms (§13.1)
- [ ] 3. `core/metrics.py` — Prometheus instrumentator + кастомные метрики (§13.2)
- [ ] 4. `main.py` — подключить Prometheus instrumentator на `/metrics`
- [ ] 5. `main.py` — расширить `/api/health/ready` проверкой миграций (§13.3)
- [ ] 6. `docker-compose.dev.yml` — обновить healthcheck на `/api/health/ready`
- [ ] 7. Тесты: unit для log filtering, integration для health ready, integration для metrics endpoint
- [ ] 8. ruff + pytest green
