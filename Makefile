# Makefile for NL2Pinecone Query Agent
# Uses uv for fast dependency management

.PHONY: help setup install run test test-batch test-primary health clean dev docker-build docker-run docker-stop samples check-env

help: ## Show this help message
	@echo "🤖 NL2Pinecone Query Agent - Available Commands"
	@echo "================================================"
	@echo "Setup & Installation:"
	@echo "  setup         - Setup uv environment and install dependencies"
	@echo "  install       - Install dependencies using uv"
	@echo "  dev           - Setup development environment"
	@echo "  install-dev   - Install development dependencies"
	@echo ""
	@echo "Running:"
	@echo "  run           - Start FastAPI server"
	@echo "  health        - Check API health"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run individual query tests"
	@echo "  test-batch    - Run comprehensive batch tests (all samples)"
	@echo "  test-primary  - Run primary requirement tests only"
	@echo "  samples       - Show all test samples"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          - Run code linting with ruff"
	@echo "  format        - Format code with black"
	@echo "  format-check  - Check code formatting"
	@echo "  type-check    - Run type checking with mypy"
	@echo "  ci            - Run full CI pipeline"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"
	@echo "  docker-stop   - Stop Docker container"
	@echo ""
	@echo "Development:"
	@echo "  clean         - Clean generated files"
	@echo "  sync          - Sync dependencies with uv"
	@echo "  freeze        - Generate requirements.txt"
	@echo "  env-create    - Create .env file from template"
	@echo ""
	@echo "💡 Make sure to set GEMINI_API_KEY in .env file!"

# Setup and installation
setup: ## Setup uv environment and install dependencies
	@echo "🚀 Setting up NL2Pinecone Query Agent..."
	@which uv >/dev/null 2>&1 || (echo "❌ uv not found. Install from: https://docs.astral.sh/uv/" && exit 1)
	uv sync
	@echo "✅ Setup complete! Copy .env.example to .env and add your API keys."

install: setup ## Install dependencies with uv

dev: setup ## Setup development environment
	@echo "🛠️  Development environment ready!"

# Running the application
run: check-env ## Run the FastAPI application
	@echo "🚀 Starting FastAPI server..."
	@echo "📍 API will be available at: http://localhost:8000"
	@echo "📚 API docs at: http://localhost:8000/docs"
	uv run app.py

health: ## Check API health
	@echo "🏥 Checking API health..."
	curl -f http://localhost:8000/health || (echo "❌ API is not running. Start with: make run" && exit 1)
	@echo "\n✅ API is healthy!"

# Testing
test: check-env ## Run individual query tests
	@echo "🧪 Running individual query tests..."
	@echo "Test 1: Author + Time + Topic"
	curl -s -X POST "http://localhost:8000/query" \
		-H "Content-Type: application/json" \
		-d '{"query": "Show me articles by Alice Zhang from last year about machine learning"}' | jq .
	@echo "\nTest 2: Tags + Specific Date"
	curl -s -X POST "http://localhost:8000/query" \
		-H "Content-Type: application/json" \
		-d '{"query": "Find posts tagged with LLMs published in June, 2023"}' | jq .
	@echo "\nTest 3: Author + Topic"
	curl -s -X POST "http://localhost:8000/query" \
		-H "Content-Type: application/json" \
		-d '{"query": "Anything by John Doe on vector search?"}' | jq .

test-batch: check-env ## Run comprehensive batch tests (all samples)
	@echo "🧪 Running comprehensive batch tests..."
	@echo "📊 Testing all samples from requirements and documentation"
	uv run python test_batch.py

test-primary: check-env ## Run primary requirement tests only
	@echo "🎯 Running primary requirement tests..."
	@echo "📋 Testing core samples from project requirements"
	uv run python test_batch.py --primary

samples: ## Show all test samples
	@echo "📋 Available test samples:"
	uv run python test_samples.py

sync: ## Sync dependencies with uv
	uv sync

freeze: ## Generate requirements.txt from current environment
	uv pip freeze > requirements-freeze.txt

install-dev: ## Install development dependencies
	uv add --dev pytest pytest-asyncio httpx black ruff mypy pytest-cov

ci: lint format-check type-check test-batch ## Run full CI pipeline
	@echo "🚀 Running full CI pipeline..."
	@echo "✅ All CI checks passed!"

# Docker operations
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t nl2pinecone-agent .
	@echo "✅ Docker image built: nl2pinecone-agent"

docker-run: ## Run Docker container
	@echo "🐳 Running Docker container..."
	@echo "📍 API will be available at: http://localhost:8000"
	docker run -d \
		--name nl2pinecone-api \
		-p 8000:8000 \
		--env-file .env \
		nl2pinecone-agent
	@echo "✅ Container started. Check logs with: docker logs nl2pinecone-api"

docker-stop: ## Stop Docker container
	@echo "🛑 Stopping Docker container..."
	docker stop nl2pinecone-api 2>/dev/null || echo "Container not running"
	docker rm nl2pinecone-api 2>/dev/null || echo "Container not found"
	@echo "✅ Container stopped and removed"

# Development utilities
clean: ## Clean generated files
	@echo "🧹 Cleaning generated files..."
	rm -f batch_test_results.json
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/
	@echo "✅ Cleanup complete"

lint: ## Run code linting with ruff
	@echo "🔍 Running code linting..."
	@which ruff >/dev/null 2>&1 || (echo "Installing ruff..." && uv add --dev ruff)
	uv run ruff check .

format: ## Format code with black
	@echo "🎨 Formatting code..."
	@which black >/dev/null 2>&1 || (echo "Installing black..." && uv add --dev black)
	uv run black .

format-check: ## Check if code is formatted properly
	@which black >/dev/null 2>&1 || (echo "Installing black..." && uv add --dev black)
	uv run black --check .

type-check: ## Run type checking with mypy
	@echo "🔍 Running type checks..."
	@which mypy >/dev/null 2>&1 || (echo "Installing mypy..." && uv add --dev mypy)
	uv run mypy .

# Utility targets
.env:
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from template..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env and add your API keys!"; \
	fi

env-create: .env ## Create .env file from template

# Check dependencies before running
check-env:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make setup' and copy .env.example to .env"; \
		exit 1; \
	fi
	@if ! grep -q "GEMINI_API_KEY=" .env || grep -q "GEMINI_API_KEY=$$" .env; then \
		echo "⚠️  GEMINI_API_KEY not set in .env file. Please add your API key!"; \
	fi
