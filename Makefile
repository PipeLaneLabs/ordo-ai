# ==============================================================================
# 🛠️ MULTI-TIER AGENT ECOSYSTEM - Development Makefile
#
# Usage:
#   make setup          - Install dependencies and setup pre-commit hooks
#   make run            - Start the FastAPI application locally
#   make test           - Run all tests and generate coverage report
#   make lint           - Run all code quality checks (ruff, mypy, black)
#   make format         - Auto-format code with black and ruff
#   make security-scan  - Run bandit security scanner
#   make clean          - Remove temporary files and caches
# ==============================================================================

# ==============================================================================
# ⚙️ SETUP & INSTALLATION
# ==============================================================================

.PHONY: setup
setup:
	@echo "🚀 Initializing the project..."
	@poetry install
	@echo "🤝 Installing git hooks..."
	@poetry run pre-commit install --hook-type commit-msg
	@poetry run pre-commit install
	@echo "✅ Setup complete! Environment is ready."

# ==============================================================================
# ▶️ APPLICATION EXECUTION
# ==============================================================================

.PHONY: run
run:
	@echo "🚀 Starting FastAPI application on http://localhost:8000"
	@poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# ==============================================================================
# 🧪 TESTING & QUALITY ASSURANCE
# ==============================================================================

.PHONY: test
test:
	@echo "🧪 Running test suite..."
	@poetry run pytest tests/ --cov=src

.PHONY: lint
lint:
	@echo "🔍 Running code quality checks..."
	@echo "--- Checking formatting with Black..."
	@poetry run black --check src/ tests/
	@echo "--- Linting with Ruff..."
	@poetry run ruff check src/ tests/
	@echo "--- Type-checking with MyPy (src)..."
	@poetry run mypy src/ --strict
	@echo "--- Type-checking with MyPy (tests)..."
	@poetry run mypy tests/ --ignore-missing-imports
	@echo "✅ All checks passed!"

.PHONY: format
format:
	@echo "🎨 Auto-formatting code..."
	@poetry run black src/ tests/
	@poetry run ruff check --fix src/ tests/
	@echo "✅ Formatting complete."

.PHONY: security-scan
security-scan:
	@echo "🛡️ Running security scan with Bandit..."
	@poetry run bandit -r src/ -c .bandit -f json -o bandit-report.json
	@echo "📄 Bandit report:"
	@cat bandit-report.json || true

# ==============================================================================
# 🧹 HOUSEKEEPING
# ==============================================================================

.PHONY: clean
clean:
	@echo "🧹 Cleaning up temporary files and caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage
	@rm -rf htmlcov/
	@rm -f bandit-report.json
	@echo "✅ Clean-up complete."
old_string: