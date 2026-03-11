.PHONY: setup dev down test lint migrate seed build clean

# Development
setup:
	cp -n .env.example .env || true
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "API:      http://localhost:8000"
	@echo "Docs:     http://localhost:8000/docs"
	@echo "Frontend: http://localhost:3000"

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api

# Database
migrate:
	docker compose exec api alembic upgrade head

migrate-create:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

seed:
	docker compose exec api python -m scripts.seed_data

# Testing
test:
	docker compose exec api pytest tests/ -v --tb=short

test-unit:
	docker compose exec api pytest tests/unit/ -v

test-integration:
	docker compose exec api pytest tests/integration/ -v

test-cov:
	docker compose exec api pytest tests/ --cov=platform --cov=services --cov=modules --cov-report=term-missing

# Code quality
lint:
	docker compose exec api ruff check .
	docker compose exec api ruff format --check .

format:
	docker compose exec api ruff check --fix .
	docker compose exec api ruff format .

typecheck:
	docker compose exec api mypy platform/ services/ modules/

# Build
build:
	docker compose -f docker-compose.yml build

build-prod:
	docker build -f infrastructure/docker/Dockerfile -t healthos-api:latest .

# Clean
clean:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
