.PHONY: up down logs backend-logs db-logs frontend-logs lint test migrate keys

# Start all services
up:
	docker compose -f docker-compose.dev.yml up --build -d

# Stop all services
down:
	docker compose -f docker-compose.dev.yml down

# Tail all logs
logs:
	docker compose -f docker-compose.dev.yml logs -f

# Service-specific logs
backend-logs:
	docker compose -f docker-compose.dev.yml logs -f backend

db-logs:
	docker compose -f docker-compose.dev.yml logs -f db

frontend-logs:
	docker compose -f docker-compose.dev.yml logs -f frontend

# Lint backend
lint:
	cd backend && ruff check . && mypy app/

# Run backend tests
test:
	cd backend && pytest -v

# Run alembic migration
migrate:
	cd backend && alembic upgrade head

# Generate JWT RS256 key pair
keys:
	mkdir -p backend/keys
	openssl genpkey -algorithm RSA -out backend/keys/jwt-private.pem -pkeyopt rsa_keygen_bits:2048
	openssl rsa -pubout -in backend/keys/jwt-private.pem -out backend/keys/jwt-public.pem
	@echo "JWT keys generated in backend/keys/"
