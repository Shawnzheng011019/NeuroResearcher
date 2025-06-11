# Makefile for GPT Researcher LangGraph

.PHONY: help install test clean run-test run-example setup-env rag-setup rag-test rag-index rag-search rag-stats

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  setup-env    - Setup environment files"
	@echo "  test         - Run system tests"
	@echo "  run-example  - Run example research"
	@echo "  run-test     - Run quick test"
	@echo "  clean        - Clean up generated files"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "RAG commands:"
	@echo "  rag-setup    - Setup Milvus database for RAG"
	@echo "  rag-test     - Test RAG system"
	@echo "  rag-index    - Index documents in my-docs directory"
	@echo "  rag-search   - Search documents (requires QUERY variable)"
	@echo "  rag-stats    - Show RAG collection statistics"

# Install dependencies
install:
	pip install -r requirements.txt

# Setup environment
setup-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from template. Please edit it with your API keys."; \
	else \
		echo ".env file already exists."; \
	fi
	@mkdir -p outputs logs

# Run system tests
test:
	python test_system.py

# Run example research
run-example:
	python run_example.py

# Run quick test
run-test:
	python main.py "什么是人工智能？" --format markdown --max-sections 2 --verbose

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf */*/__pycache__/
	rm -rf *.pyc
	rm -rf */*.pyc
	rm -rf */*/*.pyc
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# Development setup
dev-install: install
	pip install pytest pytest-asyncio black flake8 mypy

# Format code
format:
	black *.py */*.py

# Lint code
lint:
	flake8 *.py */*.py --max-line-length=100 --ignore=E203,W503

# Type check
typecheck:
	mypy *.py --ignore-missing-imports

# Full development check
check: format lint typecheck test

# Install in development mode
install-dev:
	pip install -e .

# Create distribution
dist:
	python setup.py sdist bdist_wheel

# Upload to PyPI (use with caution)
upload:
	twine upload dist/*

# RAG Commands

# Setup Milvus database
rag-setup:
	@echo "Setting up Milvus database..."
	@if [ ! -f docker-compose.yml ]; then \
		wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml; \
	fi
	docker-compose up -d
	@echo "Waiting for Milvus to start..."
	sleep 10
	@echo "Milvus setup complete!"

# Test RAG system
rag-test:
	python test_rag_system.py

# Index documents
rag-index:
	@mkdir -p my-docs
	python rag_cli.py index --source ./my-docs

# Search documents
rag-search:
	@if [ -z "$(QUERY)" ]; then \
		echo "Usage: make rag-search QUERY='your search query'"; \
		echo "Example: make rag-search QUERY='machine learning'"; \
	else \
		python rag_cli.py search --query "$(QUERY)"; \
	fi

# Show RAG statistics
rag-stats:
	python rag_cli.py stats

# Setup complete RAG environment
rag-full-setup: setup-env rag-setup
	@echo "RAG environment setup complete!"
	@echo "You can now:"
	@echo "1. Add documents to ./my-docs directory"
	@echo "2. Run 'make rag-index' to index them"
	@echo "3. Run 'make rag-search QUERY=\"your query\"' to search"
