.PHONY: help dev up down migrate seed test lint format clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start dev environment
	docker compose up -d postgres redis kafka qdrant neo4j
	@echo "Waiting for services..."
	@sleep 5
	uvicorn platform.api.main:app --host 0.0.0.0 --port 8000 --reload

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	alembic revision --autogenerate -m "$(msg)"

seed: ## Seed database with sample data
	python -m scripts.seed_data

simulate: ## Run device simulator
	python -m scripts.simulate_devices

test: ## Run tests
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=platform --cov=modules --cov-report=html --cov-report=term

lint: ## Run linter
	ruff check .

format: ## Format code
	ruff format .

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	rm -rf htmlcov .coverage
