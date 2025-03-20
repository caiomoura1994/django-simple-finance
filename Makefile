.PHONY: help install install-dev migrate makemigrations superuser run run-prod shell test clean lint format collectstatic

# Variables
PYTHON = python
MANAGE = $(PYTHON) manage.py
VENV = venv
VENV_BIN = $(VENV)/bin
PIP = $(VENV_BIN)/pip

help: ## Show this help message
	@echo 'Usage:'
	@echo '  make <target>'
	@echo ''
	@echo 'Targets:'
	@awk -F ':|##' '/^[^\t].+?:.*?##/ { printf "  %-20s %s\n", $$1, $$NF }' $(MAKEFILE_LIST)

$(VENV)/bin/activate: ## Create virtual environment
	python -m venv $(VENV)
	$(PIP) install --upgrade pip

active-venv: $(VENV)/bin/activate ## Create virtual environment

install: venv ## Install production dependencies
	. $(VENV_BIN)/activate && $(PIP) install -r requirements.txt

install-dev: venv ## Install development dependencies
	. $(VENV_BIN)/activate && $(PIP) install -r requirements_dev.txt

migrate: ## Apply database migrations
	. $(VENV_BIN)/activate && $(MANAGE) migrate

makemigrations: ## Create database migrations
	. $(VENV_BIN)/activate && $(MANAGE) makemigrations

superuser: ## Create a superuser
	. $(VENV_BIN)/activate && $(MANAGE) createsuperuser

run: ## Run development server
	. $(VENV_BIN)/activate && $(MANAGE) runserver

run-prod: ## Run production server
	. $(VENV_BIN)/activate && DJANGO_ENV=production $(MANAGE) runserver

shell: ## Open Django shell
	. $(VENV_BIN)/activate && $(MANAGE) shell

test: ## Run tests
	. $(VENV_BIN)/activate && pytest

test-watch: ## Run tests in watch mode
	test --watch

clean: ## Remove Python and coverage artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "db.sqlite3" -delete

lint: ## Check code style
	. $(VENV_BIN)/activate && flake8 .
	. $(VENV_BIN)/activate && isort . --check-only

format: ## Format code
	. $(VENV_BIN)/activate && black .
	. $(VENV_BIN)/activate && isort .

collectstatic: ## Collect static files
	. $(VENV_BIN)/activate && $(MANAGE) collectstatic --noinput

# Database commands for development
db-dev-reset: ## Reset development database (SQLite)
	rm -f db.sqlite3
	. $(VENV_BIN)/activate && $(MANAGE) migrate

# Development setup
setup-dev: install-dev migrate ## Setup development environment

# Production setup
setup-prod: install migrate collectstatic ## Setup production environment 