"""
Custom Exception Classes

Defines all custom exceptions used throughout the workflow system.
Organized by error category for clear error handling and routing.
"""

from typing import Any


class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""


class BudgetExhaustedError(WorkflowError):
    """Raised when token or cost budget is exhausted."""

    def __init__(
        self,
        limit: float,
        requested: float = 0.0,
        used: float | None = None,
        budget_type: str = "tokens",
    ) -> None:
        self.budget_type = budget_type
        self.limit = limit
        self.requested = requested
        self.used = used if used is not None else requested
        super().__init__(
            f"Budget exhausted: {self.used:,.0f} {budget_type} used / "
            f"{limit:,.0f} limit"
        )


class AgentRejectionError(WorkflowError):
    """Raised when an agent's output is rejected by a validator."""

    def __init__(
        self,
        agent: str,
        validator: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.agent = agent
        self.validator = validator
        self.reason = reason
        self.details = details or {}
        super().__init__(f"Agent '{agent}' rejected by '{validator}': {reason}")


class ValidationError(WorkflowError):
    """Raised when validation fails (requirements, architecture, tests, etc.)."""

    def __init__(self, validation_type: str, failures: list[str]) -> None:
        self.validation_type = validation_type
        self.failures = failures
        super().__init__(
            f"{validation_type} validation failed: {len(failures)} issue(s)"
        )


class SecurityViolationError(WorkflowError):
    """Raised when security vulnerabilities are detected."""

    def __init__(self, vulnerabilities: list[str], severity: str = "HIGH") -> None:
        self.vulnerabilities = vulnerabilities
        self.severity = severity
        super().__init__(
            f"Security violations detected ({severity}): {', '.join(vulnerabilities)}"
        )


class CheckpointNotFoundError(WorkflowError):
    """Raised when checkpoint ID not found."""

    def __init__(
        self, checkpoint_id: str, details: dict[str, Any] | None = None
    ) -> None:
        self.checkpoint_id = checkpoint_id
        self.details = details or {}
        super().__init__(f"Checkpoint not found: {checkpoint_id}")


class LLMProviderError(WorkflowError):
    """Raised when LLM provider fails."""

    def __init__(
        self,
        message: str,
        provider: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(message)


class InvalidTaskGraphError(WorkflowError):
    """Raised when task dependency graph has cycles."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Circular task dependency: {' → '.join(cycle)}")


class DatabaseConnectionError(WorkflowError):
    """Raised when database connection fails."""

    def __init__(
        self,
        database: str,
        operation: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.database = database
        self.operation = operation
        self.details = details or {}
        message = f"Database connection failed ({database})"
        if operation:
            message += f" during {operation}"
        super().__init__(message)


class FileGenerationError(WorkflowError):
    """Raised when file generation fails."""

    def __init__(self, file_path: str, reason: str) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"File generation failed for '{file_path}': {reason}")


class InfiniteLoopDetectedError(WorkflowError):
    """Raised when workflow enters infinite loop (too many rejections)."""

    def __init__(
        self,
        agent_name: str = "",
        max_iterations: int = 3,
        current_state: str = "",
        rejection_count: int | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.max_iterations = max_iterations
        self.current_state = current_state
        self.rejection_count = rejection_count or max_iterations
        message = f"Infinite loop detected: {self.rejection_count} iterations"
        if agent_name:
            message += f" in {agent_name}"
        message += f" (max: {max_iterations})"
        super().__init__(message)


class HumanApprovalTimeoutError(WorkflowError):
    """Raised when human approval times out."""

    def __init__(
        self,
        gate_name: str,
        timeout_seconds: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.gate_name = gate_name
        self.timeout_seconds = timeout_seconds
        self.details = details or {}
        timeout_hours = timeout_seconds / 3600
        super().__init__(
            f"Human approval timeout at '{gate_name}' "
            f"(waited {timeout_hours:.1f} hours)"
        )


class ConfigurationError(WorkflowError):
    """Raised when configuration is invalid."""

    def __init__(self, config_name: str, reason: str) -> None:
        self.config_name = config_name
        self.reason = reason
        super().__init__(f"Configuration error in '{config_name}': {reason}")


class ArtifactStorageError(WorkflowError):
    """Raised when artifact storage operations fail."""

    def __init__(self, operation: str, artifact_path: str, reason: str) -> None:
        self.operation = operation
        self.artifact_path = artifact_path
        self.reason = reason
        super().__init__(
            f"Artifact storage '{operation}' failed for '{artifact_path}': {reason}"
        )


class StorageError(WorkflowError):
    """Raised when MinIO storage operations fail."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CacheError(WorkflowError):
    """Raised when Redis cache operations fail."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
