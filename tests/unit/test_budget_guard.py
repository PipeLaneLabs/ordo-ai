"""
Unit Tests for Budget Guard

Tests token and cost budget tracking, enforcement,
and warning threshold logic.

NOTE: BudgetGuard methods require WorkflowState parameter.
These tests focus on initialization and basic validation.
Full integration tests will be in integration tests.
"""

from src.orchestration.budget_guard import BudgetGuard


class TestBudgetGuardInitialization:
    """Test BudgetGuard initialization."""

    def test_default_initialization(self):
        """Test initialization with default settings."""
        guard = BudgetGuard()
        # Defaults from settings.max_tokens_per_workflow, max_monthly_budget_usd
        assert guard.max_tokens_per_workflow > 0
        assert guard.max_monthly_budget_usd > 0
        assert guard.alert_threshold_pct == 75.0

    def test_custom_initialization(self):
        """Test initialization with custom values."""
        guard = BudgetGuard(
            max_tokens_per_workflow=100000,
            max_monthly_budget_usd=10.0,
            alert_threshold_pct=80.0,
        )
        assert guard.max_tokens_per_workflow == 100000
        assert guard.max_monthly_budget_usd == 10.0
        assert guard.alert_threshold_pct == 80.0

    def test_monthly_usage_initialized(self):
        """Test that monthly usage tracking is initialized."""
        guard = BudgetGuard()
        assert hasattr(guard, "current_month_used_usd")
        assert guard.current_month_used_usd == 0.0
