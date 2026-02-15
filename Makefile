# ==========================================================
# 🛠️ MULTI-TIER AGENT ECOSYSTEM - CONTROL PANEL
# ==========================================================

.PHONY: setup
setup:
	@echo "🚀 Initializing the Factory..."
	@poetry install
	@poetry run pre-commit install --hook-type commit-msg
	@echo "✅ Setup complete! Local bouncers are active."

.PHONY: test
test:
	@echo "🧪 Running Test Suite..."
	@poetry run pytest tests/ --cov=src

.PHONY: lint
lint:
	@echo "🔍 Running Code Quality Checks..."
	@poetry run ruff check .
	@poetry run mypy src/