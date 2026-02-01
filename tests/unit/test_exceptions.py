"""
Unit Tests for Custom Exceptions

Tests all custom exception classes for correct initialization,
error messages, and attribute storage.
"""

from src.exceptions import (
    AgentRejectionError,
    BudgetExhaustedError,
    ConfigurationError,
    DatabaseConnectionError,
    InfiniteLoopDetectedError,
    LLMProviderError,
    SecurityViolationError,
    ValidationError,
    WorkflowError,
)


class TestWorkflowError:
    """Test base WorkflowError exception."""

    def test_workflow_error_is_exception(self):
        """WorkflowError should inherit from Exception."""
        error = WorkflowError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestBudgetExhaustedError:
    """Test budget exhaustion exception."""

    def test_token_budget_exhausted(self):
        """Test token budget exhaustion message."""
        error = BudgetExhaustedError(used=100000, limit=50000, budget_type="tokens")
        assert error.used == 100000
        assert error.limit == 50000
        assert error.budget_type == "tokens"
        assert "100,000" in str(error)
        assert "50,000" in str(error)
        assert "tokens" in str(error)

    def test_cost_budget_exhausted(self):
        """Test cost budget exhaustion message."""
        error = BudgetExhaustedError(used=25.50, limit=20.00, budget_type="USD")
        assert error.used == 25.50
        assert error.limit == 20.00
        assert error.budget_type == "USD"
        assert "26" in str(error) or "25" in str(error)  # Rounded display
        assert "USD" in str(error)

    def test_default_budget_type(self):
        """Test default budget_type is 'tokens'."""
        error = BudgetExhaustedError(used=1000, limit=500)
        assert error.budget_type == "tokens"


class TestAgentRejectionError:
    """Test agent rejection exception."""

    def test_basic_rejection(self):
        """Test basic rejection without details."""
        error = AgentRejectionError(
            agent="Software Engineer",
            validator="Static Analysis Agent",
            reason="Type errors found",
        )
        assert error.agent == "Software Engineer"
        assert error.validator == "Static Analysis Agent"
        assert error.reason == "Type errors found"
        assert error.details == {}
        assert "Software Engineer" in str(error)
        assert "Static Analysis Agent" in str(error)
        assert "Type errors found" in str(error)

    def test_rejection_with_details(self):
        """Test rejection with error details."""
        details = {"file": "main.py", "line": 45, "error_type": "type-arg"}
        error = AgentRejectionError(
            agent="Software Engineer",
            validator="Static Analysis Agent",
            reason="Type errors found",
            details=details,
        )
        assert error.details == details
        assert error.details["file"] == "main.py"
        assert error.details["line"] == 45

    def test_rejection_none_details(self):
        """Test that None details becomes empty dict."""
        error = AgentRejectionError(
            agent="Software Engineer",
            validator="Static Analysis Agent",
            reason="Type errors found",
            details=None,
        )
        assert error.details == {}


class TestValidationError:
    """Test validation exception."""

    def test_single_failure(self):
        """Test validation error with single failure."""
        error = ValidationError(
            validation_type="requirements", failures=["Missing acceptance criteria"]
        )
        assert error.validation_type == "requirements"
        assert len(error.failures) == 1
        assert "Missing acceptance criteria" in error.failures
        assert "requirements" in str(error).lower()

    def test_multiple_failures(self):
        """Test validation error with multiple failures."""
        failures = [
            "Missing acceptance criteria",
            "Conflicting requirements FR-001 and FR-002",
            "NFR-003 not measurable",
        ]
        error = ValidationError(validation_type="requirements", failures=failures)
        assert error.validation_type == "requirements"
        assert len(error.failures) == 3
        assert all(f in error.failures for f in failures)
        assert "3 issue" in str(error) or "3 failures" in str(error)


class TestConfigurationError:
    """Test configuration exception."""

    def test_missing_config(self):
        """Test missing configuration error."""
        error = ConfigurationError(
            config_name="OPENROUTER_API_KEY", reason="Environment variable not set"
        )
        assert error.config_name == "OPENROUTER_API_KEY"
        assert error.reason == "Environment variable not set"
        assert "OPENROUTER_API_KEY" in str(error)
        assert "not set" in str(error)

    def test_invalid_config(self):
        """Test invalid configuration error."""
        error = ConfigurationError(
            config_name="MAX_TOKENS_PER_WORKFLOW",
            reason="Must be positive integer, got -1000",
        )
        assert error.config_name == "MAX_TOKENS_PER_WORKFLOW"
        assert "positive integer" in error.reason


class TestSecurityViolationError:
    """Test security violation exception."""

    def test_single_vulnerability(self):
        """Test single security vulnerability."""
        error = SecurityViolationError(
            vulnerabilities=["SQL injection in user_service.py:45"],
            severity="CRITICAL",
        )
        assert len(error.vulnerabilities) == 1
        assert error.severity == "CRITICAL"
        assert "SQL injection" in str(error)

    def test_multiple_vulnerabilities(self):
        """Test multiple security vulnerabilities."""
        vulns = ["XSS in routes.py:23", "CSRF token missing", "Weak password policy"]
        error = SecurityViolationError(vulnerabilities=vulns, severity="HIGH")
        assert len(error.vulnerabilities) == 3
        assert error.severity == "HIGH"


class TestDatabaseConnectionError:
    """Test database connection exception."""

    def test_connection_refused(self):
        """Test connection refused error."""
        error = DatabaseConnectionError(
            database="PostgreSQL",
            operation="connect",
            details={"error": "Connection refused on port 5432"},
        )
        assert error.database == "PostgreSQL"
        assert error.operation == "connect"
        assert "PostgreSQL" in str(error)
        assert "connect" in str(error)

    def test_authentication_failed(self):
        """Test authentication failure."""
        error = DatabaseConnectionError(
            database="Redis",
            operation="auth",
            details={"reason": "Authentication failed"},
        )
        assert error.database == "Redis"
        assert error.operation == "auth"
        assert "Redis" in str(error)


class TestLLMProviderError:
    """Test LLM provider exception."""

    def test_provider_error_with_model(self):
        """Test LLM provider error with model specified."""
        error = LLMProviderError(
            message="API rate limit exceeded",
            provider="OpenRouter",
            details={"model": "gpt-4"},
        )
        assert error.provider == "OpenRouter"
        assert error.message == "API rate limit exceeded"
        assert error.details["model"] == "gpt-4"
        assert "API rate limit exceeded" in str(error)

    def test_provider_error_without_model(self):
        """Test LLM provider error without model specified."""
        error = LLMProviderError(message="Invalid API key", provider="Google")
        assert error.provider == "Google"
        assert error.details == {}
        assert "Invalid API key" in str(error)


class TestInfiniteLoopDetectedError:
    """Test infinite loop detection exception."""

    def test_default_max_rejections(self):
        """Test default max rejections limit."""
        error = InfiniteLoopDetectedError(agent_name="TestAgent", rejection_count=5)
        assert error.rejection_count == 5
        assert error.max_iterations == 3
        assert "5 iterations" in str(error)
        assert "TestAgent" in str(error)

    def test_custom_max_rejections(self):
        """Test custom max rejections limit."""
        error = InfiniteLoopDetectedError(rejection_count=10, max_iterations=5)
        assert error.rejection_count == 10
        assert error.max_iterations == 5
