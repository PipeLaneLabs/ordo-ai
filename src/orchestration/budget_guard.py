"""
Budget Guard

Enforces token and cost budgets across workflows.
Implements 75% warning threshold and 100% hard limit blocking.
"""

from typing import Any

import structlog

from src.config import settings
from src.exceptions import BudgetExhaustedError
from src.orchestration.state import WorkflowState
from src.storage.cache import RedisCache


logger = structlog.get_logger()


class BudgetGuard:
    """
    Token and cost budget enforcement.

    Responsibilities:
    - Check budget before LLM operations
    - Enforce workflow-level token limits
    - Enforce monthly cost limits
    - Alert at 75% threshold
    - Block at 100% hard limit

    Usage:
        budget_guard = BudgetGuard()
        result = budget_guard.reserve_budget(
            operation_name="software_engineer_generate",
            estimated_tokens=15000,
            estimated_cost_usd=0.003,
            workflow_state=state
        )
        if not result["allowed"]:
            raise BudgetExhaustedError(...)
    """

    def __init__(
        self,
        max_tokens_per_workflow: int | None = None,
        max_monthly_budget_usd: float | None = None,
        alert_threshold_pct: float | None = None,
        cache: RedisCache | None = None,
    ) -> None:
        """
        Initialize Budget Guard.

        Args:
            max_tokens_per_workflow: Max tokens per workflow (default: settings)
            max_monthly_budget_usd: Max monthly budget USD (default: settings)
            alert_threshold_pct: Alert threshold percentage (default: from settings)
            cache: Redis cache instance (default: creates new RedisCache)
        """
        self.max_tokens_per_workflow = (
            max_tokens_per_workflow or settings.max_tokens_per_workflow
        )
        self.max_monthly_budget_usd = (
            max_monthly_budget_usd or settings.max_monthly_budget_usd
        )
        self.alert_threshold_pct = (
            alert_threshold_pct or settings.budget_alert_threshold_pct
        )
        self.cache = cache or RedisCache()
        self._cache_connected = False

        # TODO (future): Load actual monthly usage from database
        # For now, track in-memory (resets on restart)
        self.current_month_used_usd = 0.0

    def reserve_budget(
        self,
        operation_name: str,
        estimated_tokens: int,
        estimated_cost_usd: float,
        workflow_state: WorkflowState,
    ) -> dict[str, Any]:
        """
        Reserve budget before LLM operation.

        This method checks both workflow-level and monthly budget limits.
        If the budget is sufficient, it returns a dictionary with information
        about the reservation. If the budget is exceeded, it raises an exception.

        Args:
            operation_name: Name of operation (e.g., "software_engineer_generate_code")
            estimated_tokens: Estimated token usage
            estimated_cost_usd: Estimated cost in USD
            workflow_state: Current workflow state

        Returns:
            Dict with keys:
                - allowed: bool (True if operation can proceed)
                - reason: str (explanation)
                - alert: str | None (warning message if at threshold)

        Raises:
            BudgetExhaustedError: If hard limit reached (100%)
        """
        log = logger.bind(
            workflow_id=workflow_state["workflow_id"],
            operation=operation_name,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

        # Check workflow-level token budget
        remaining_tokens = workflow_state["budget_remaining_tokens"]
        if estimated_tokens > remaining_tokens:
            log.error(
                "workflow_token_budget_exceeded",
                used=workflow_state["budget_used_tokens"],
                remaining=remaining_tokens,
                limit=self.max_tokens_per_workflow,
            )
            raise BudgetExhaustedError(
                used=workflow_state["budget_used_tokens"],
                limit=self.max_tokens_per_workflow,
                budget_type="tokens",
            )

        # Check workflow-level cost budget
        remaining_usd = workflow_state["budget_remaining_usd"]
        if estimated_cost_usd > remaining_usd:
            log.error(
                "workflow_cost_budget_exceeded",
                used=workflow_state["budget_used_usd"],
                remaining=remaining_usd,
                limit=self.max_monthly_budget_usd,
            )
            raise BudgetExhaustedError(
                used=workflow_state["budget_used_usd"],
                limit=self.max_monthly_budget_usd,
                budget_type="USD",
            )

        # Check monthly cost budget
        projected_monthly_total = self.current_month_used_usd + estimated_cost_usd
        if projected_monthly_total > self.max_monthly_budget_usd:
            log.error(
                "monthly_budget_exceeded",
                current_month_used=self.current_month_used_usd,
                estimated_cost=estimated_cost_usd,
                limit=self.max_monthly_budget_usd,
            )
            raise BudgetExhaustedError(
                used=self.current_month_used_usd,
                limit=self.max_monthly_budget_usd,
                budget_type="monthly USD",
            )

        # Calculate usage percentages
        token_usage_pct = (
            (workflow_state["budget_used_tokens"] + estimated_tokens)
            / self.max_tokens_per_workflow
            * 100
        )
        cost_usage_pct = (
            (workflow_state["budget_used_usd"] + estimated_cost_usd)
            / self.max_monthly_budget_usd
            * 100
        )

        # Check if at warning threshold
        alert_message = None
        if token_usage_pct >= self.alert_threshold_pct:
            alert_message = (
                f"Token budget at {token_usage_pct:.1f}% "
                f"({workflow_state['budget_used_tokens']:,} / "
                f"{self.max_tokens_per_workflow:,})"
            )
            log.warning(
                "budget_threshold_warning",
                budget_type="tokens",
                usage_pct=token_usage_pct,
                threshold_pct=self.alert_threshold_pct,
            )
        elif cost_usage_pct >= self.alert_threshold_pct:
            alert_message = (
                f"Cost budget at {cost_usage_pct:.1f}% "
                f"(${workflow_state['budget_used_usd']:.2f} / "
                f"${self.max_monthly_budget_usd:.2f})"
            )
            log.warning(
                "budget_threshold_warning",
                budget_type="cost",
                usage_pct=cost_usage_pct,
                threshold_pct=self.alert_threshold_pct,
            )

        # Budget reservation successful
        log.info(
            "budget_reserved",
            token_usage_pct=token_usage_pct,
            cost_usage_pct=cost_usage_pct,
        )

        return {
            "allowed": True,
            "reason": "Budget available",
            "alert": alert_message,
        }

    async def check_budget(
        self,
        workflow_state: WorkflowState | None = None,
        tokens_required: int | None = None,
        cost_required: float | None = None,
        cost_usd: float | None = None,
        operation_name: str | None = None,
        estimated_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        workflow_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Check if budget allows operation (async version with Redis).

        Supports two calling conventions:
        1. With workflow_state: check_budget(workflow_state=state, tokens_required=100)
        2. With workflow_id: check_budget(workflow_id="abc", estimated_tokens=100, estimated_cost_usd=0.01)

        Args:
            workflow_state: Current workflow state (legacy parameter)
            tokens_required: Tokens required (legacy parameter, same as estimated_tokens)
            cost_required: Cost required (legacy parameter, same as estimated_cost_usd)
            cost_usd: Cost in USD (alternative name for cost_required)
            operation_name: Name of operation
            estimated_tokens: Estimated token usage
            estimated_cost_usd: Estimated cost in USD
            workflow_id: Workflow ID for tracking

        Returns:
            Dict with keys:
                - allowed: bool (True if operation can proceed)
                - reason: str (explanation)
                - remaining_tokens: int
                - remaining_cost_usd: float

        Raises:
            BudgetExhaustedError: If hard limit reached
        """
        # Handle legacy parameter names - cost_usd is an alias for cost_required
        cost_param = cost_usd or cost_required or estimated_cost_usd or 0.0

        # Handle legacy parameter names
        if workflow_state is not None:
            # Legacy: called with workflow_state
            workflow_id = workflow_state["workflow_id"]
            tokens_used = workflow_state["budget_used_tokens"]
            cost_used = workflow_state["budget_used_usd"]
            tokens = tokens_required or estimated_tokens or 0
            cost = cost_param
        else:
            # New style: called with workflow_id
            if workflow_id is None:
                raise ValueError(
                    "Either workflow_state or workflow_id must be provided"
                )

            await self._ensure_cache_connected()

            # Get current budget from Redis
            budget_key = f"budget:workflow:{workflow_id}"
            budget_data = await self.cache.get(budget_key)

            if budget_data:
                import json

                budget = json.loads(budget_data)
                tokens_used = budget.get("tokens_used", 0)
                cost_used = budget.get("cost_used", 0.0)
            else:
                tokens_used = 0
                cost_used = 0.0

            tokens = estimated_tokens or 0
            cost = cost_param

        log = logger.bind(
            workflow_id=workflow_id,
            operation=operation_name or "check_budget",
            estimated_tokens=tokens,
            estimated_cost_usd=cost,
        )

        # Calculate remaining
        remaining_tokens = self.max_tokens_per_workflow - tokens_used
        remaining_cost = self.max_monthly_budget_usd - cost_used

        # Check token budget
        if tokens > remaining_tokens:
            log.error(
                "workflow_token_budget_exceeded",
                used=tokens_used,
                remaining=remaining_tokens,
                limit=self.max_tokens_per_workflow,
            )
            raise BudgetExhaustedError(
                used=tokens_used,
                limit=self.max_tokens_per_workflow,
                budget_type="tokens",
            )

        # Check cost budget
        if cost > remaining_cost:
            log.error(
                "workflow_cost_budget_exceeded",
                used=cost_used,
                remaining=remaining_cost,
                limit=self.max_monthly_budget_usd,
            )
            raise BudgetExhaustedError(
                used=cost_used,
                limit=self.max_monthly_budget_usd,
                budget_type="USD",
            )

        log.info(
            "budget_check_passed",
            remaining_tokens=remaining_tokens,
            remaining_cost=remaining_cost,
        )

        return {
            "allowed": True,
            "reason": "Budget available",
            "remaining_tokens": remaining_tokens,
            "remaining_cost_usd": remaining_cost,
        }

    async def reserve_budget_async(
        self,
        operation_name: str,
        estimated_tokens: int,
        estimated_cost_usd: float,
        workflow_id: str,
    ) -> dict[str, Any]:
        """
        Reserve budget and persist to Redis (async version).

        This method both checks and reserves budget in a single operation.
        The reservation is stored in Redis for distributed tracking.

        Args:
            operation_name: Name of operation
            estimated_tokens: Estimated token usage
            estimated_cost_usd: Estimated cost in USD
            workflow_id: Workflow ID for tracking

        Returns:
            Dict with reservation details

        Raises:
            BudgetExhaustedError: If hard limit reached
        """
        await self._ensure_cache_connected()

        # Check budget first
        check_result = await self.check_budget(
            workflow_state=None,
            operation_name=operation_name,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

        # Reserve budget in Redis
        budget_key = f"budget:workflow:{workflow_id}"
        budget_data = await self.cache.get(budget_key)

        if budget_data:
            import json

            budget = json.loads(budget_data)
            tokens_used = budget.get("tokens_used", 0)
            cost_used = budget.get("cost_used", 0.0)
        else:
            tokens_used = 0
            cost_used = 0.0

        # Update budget
        new_budget = {
            "tokens_used": tokens_used + estimated_tokens,
            "cost_used": cost_used + estimated_cost_usd,
            "last_operation": operation_name,
            "last_updated": str(logger.get_logger().bind().new().current_timestamp),
        }

        import json

        await self.cache.set(
            budget_key, json.dumps(new_budget), ttl_seconds=86400
        )  # 24h TTL

        logger.info(
            "budget_reserved_async",
            workflow_id=workflow_id,
            operation=operation_name,
            tokens_reserved=estimated_tokens,
            cost_reserved=estimated_cost_usd,
            total_tokens=new_budget["tokens_used"],
            total_cost=new_budget["cost_used"],
        )

        return {
            "allowed": True,
            "reserved": True,
            "tokens_reserved": estimated_tokens,
            "cost_reserved": estimated_cost_usd,
            **check_result,
        }

    async def _ensure_cache_connected(self) -> None:
        """Ensure Redis cache is connected."""
        if not self._cache_connected:
            try:
                await self.cache.connect()
                self._cache_connected = True
            except Exception as e:
                logger.warning(
                    "cache_connection_failed",
                    error=str(e),
                    fallback="in-memory tracking",
                )
                # Continue without Redis - fall back to in-memory tracking

    def record_usage(
        self,
        operation_name: str,
        tokens_used: int,
        cost_usd: float,
        workflow_state: WorkflowState,
        agent_name: str | None = None,
        actual_tokens: int | None = None,
        actual_cost_usd: float | None = None,
    ) -> None:
        """
        Record actual LLM usage after operation completes.

        This updates monthly tracking (in-memory for now).
        Workflow state budget is updated separately via update_budget() reducer.

        Args:
            operation_name: Name of operation for tracking
            tokens_used: Actual tokens consumed
            cost_usd: Actual cost in USD
            workflow_state: Current workflow state
            agent_name: Agent that consumed the budget
                (optional, defaults to operation_name)
            actual_tokens: Alias for tokens_used (legacy parameter)
            actual_cost_usd: Alias for cost_usd (legacy parameter)
        """
        # Support legacy parameter names
        tokens = actual_tokens if actual_tokens is not None else tokens_used
        cost = actual_cost_usd if actual_cost_usd is not None else cost_usd
        agent = agent_name if agent_name is not None else operation_name

        self.current_month_used_usd += cost

        logger.info(
            "budget_usage_recorded",
            workflow_id=workflow_state["workflow_id"],
            agent_name=agent,
            operation_name=operation_name,
            tokens_consumed=tokens,
            cost_usd=cost,
            total_workflow_tokens=workflow_state["budget_used_tokens"] + tokens,
            total_workflow_cost=workflow_state["budget_used_usd"] + cost,
            total_month_cost=self.current_month_used_usd,
        )

    def get_budget_summary(self, workflow_state: WorkflowState) -> dict[str, Any]:
        """
        Get budget summary for workflow.

        Args:
            workflow_state: Current workflow state

        Returns:
            Dict with budget usage statistics
        """
        token_usage_pct = (
            workflow_state["budget_used_tokens"] / self.max_tokens_per_workflow * 100
        )
        cost_usage_pct = (
            workflow_state["budget_used_usd"] / self.max_monthly_budget_usd * 100
        )

        return {
            "tokens": {
                "used": workflow_state["budget_used_tokens"],
                "remaining": workflow_state["budget_remaining_tokens"],
                "limit": self.max_tokens_per_workflow,
                "usage_pct": token_usage_pct,
                "alert_threshold_pct": self.alert_threshold_pct,
                "at_threshold": token_usage_pct >= self.alert_threshold_pct,
            },
            "cost": {
                "used_usd": workflow_state["budget_used_usd"],
                "remaining_usd": workflow_state["budget_remaining_usd"],
                "limit_usd": self.max_monthly_budget_usd,
                "usage_pct": cost_usage_pct,
                "alert_threshold_pct": self.alert_threshold_pct,
                "at_threshold": cost_usage_pct >= self.alert_threshold_pct,
            },
            "monthly": {
                "used_usd": self.current_month_used_usd,
                "limit_usd": self.max_monthly_budget_usd,
                "remaining_usd": self.max_monthly_budget_usd
                - self.current_month_used_usd,
            },
            "per_agent": workflow_state["agent_token_usage"],
        }


# Global budget guard instance
budget_guard = BudgetGuard()
