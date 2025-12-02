.PHONY: help dev build test lint migrate shell clean install format check

# Default target
help:
	@echo "OpenAPI Showcase - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Development:"
	@echo "  make dev        - Start all services in development mode"
	@echo "  make build      - Build Docker images"
	@echo "  make shell      - Open a shell in the app container"
	@echo "  make install    - Install Python dependencies locally"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run all tests"
	@echo "  make test-unit  - Run unit tests only"
	@echo "  make test-prop  - Run property-based tests only"
	@echo "  make test-cov   - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint       - Run linter (ruff)"
	@echo "  make format     - Format code with ruff"
	@echo "  make check      - Run all checks (lint, type check)"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run database migrations (upgrade to head)"
	@echo "  make migrate-down - Rollback one migration"
	@echo "  make migrate-reset- Rollback all migrations"
	@echo "  make migrate-new  - Create a new migration"
	@echo "  make migrate-history - Show migration history"
	@echo "  make migrate-current - Show current migration"
	@echo "  make migrate-docker  - Run migrations in Docker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Remove containers, volumes, and cache"

# ============================================
# Development
# ============================================
dev:
	docker compose up --build

dev-detached:
	docker compose up --build -d

build:
	docker compose build

shell:
	docker compose exec auth-api /bin/bash

install:
	pip install -e ".[dev]"

# ============================================
# Testing
# ============================================
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-prop:
	pytest tests/properties/ -v -m property

test-cov:
	pytest tests/ -v --cov=apps --cov=shared --cov-report=html --cov-report=term-missing

test-docker:
	docker compose exec auth-api pytest tests/ -v

# ============================================
# Code Quality
# ============================================
lint:
	ruff check apps/ shared/ tests/

format:
	ruff format apps/ shared/ tests/
	ruff check --fix apps/ shared/ tests/

check: lint
	mypy apps/ shared/

# ============================================
# Database
# ============================================
migrate:
	alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-down:
	alembic downgrade -1

migrate-reset:
	alembic downgrade base

migrate-history:
	alembic history --verbose

migrate-current:
	alembic current

migrate-docker:
	docker compose run --rm migrations

# ============================================
# Individual API Services
# ============================================
run-auth:
	uvicorn apps.auth.main:app --reload --port 8001

run-orders:
	uvicorn apps.orders.main:app --reload --port 8002

run-files:
	uvicorn apps.file_processor.main:app --reload --port 8003

run-notifications:
	uvicorn apps.notifications.main:app --reload --port 8004

run-webhooks:
	uvicorn apps.webhook_tester.main:app --reload --port 8005

# ============================================
# Celery
# ============================================
celery-worker:
	celery -A shared.celery_app worker --loglevel=info

celery-beat:
	celery -A shared.celery_app beat --loglevel=info

celery-flower:
	celery -A shared.celery_app flower --port=5555

# ============================================
# Cleanup
# ============================================
clean:
	docker compose down -v --remove-orphans
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# ============================================
# Docker Logs
# ============================================
logs:
	docker compose logs -f

logs-auth:
	docker compose logs -f auth-api

logs-orders:
	docker compose logs -f orders-api

logs-celery:
	docker compose logs -f celery-worker
