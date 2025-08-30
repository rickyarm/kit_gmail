.PHONY: help install install-dev test test-cov lint format clean build publish

help: ## Show help message
	@echo "Kit Gmail - Makefile commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt
	pip install -e .

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt
	pip install -e .
	pre-commit install

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=kit_gmail --cov-report=html --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

lint: ## Run linting tools
	flake8 src/ tests/
	mypy src/
	bandit -r src/ -ll

format: ## Format code
	black src/ tests/
	isort src/ tests/

format-check: ## Check code formatting
	black --check src/ tests/
	isort --check-only src/ tests/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: ## Build package
	python -m build

publish-test: ## Publish to test PyPI
	python -m twine upload --repository testpypi dist/*

publish: ## Publish to PyPI
	python -m twine upload dist/*

setup-dev: install-dev ## Complete development setup
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation"

check: format-check lint test ## Run all checks (format, lint, test)

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

init-venv: ## Initialize virtual environment
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "source venv/bin/activate  # Linux/macOS"
	@echo "venv\\Scripts\\activate     # Windows"
	@echo "Then run: make setup-dev"

security: ## Run security checks
	bandit -r src/ -ll