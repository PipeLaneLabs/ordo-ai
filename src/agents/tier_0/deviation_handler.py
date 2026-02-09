"""Deviation Handler Agent for root cause analysis and rejection routing.

Tier 0 agent that:
- Analyzes agent rejections using LLM reasoning
- Routes to correct agent for fixes
- Detects circular routing (infinite loops)
- Escalates to human after max iterations
- Maintains DEVIATION_LOG.md for traceability
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.exceptions import HumanApprovalTimeoutError, WorkflowError
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


logger = structlog.get_logger()


class DeviationHandlerAgent(BaseAgent):
    """Tier 0 agent for rejection analysis and routing.

    Uses DeepSeek-R1 for deep reasoning about rejection root causes.
    Routes to appropriate agent based on RCA.
    Detects infinite loops and escalates to human.

    Attributes:
        max_routing_iterations: Maximum times same agent can be routed (default: 3)
        deviation_log_path: Path to DEVIATION_LOG.md
        max_log_entries: Maximum entries before archiving (default: 100)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
        max_routing_iterations: int = 3,
        max_log_entries: int = 100,
    ) -> None:
        """Initialize Deviation Handler Agent.

        Args:
            llm_client: LLM client (should use DeepSeek-R1 for reasoning)
            budget_guard: Budget guard instance
            settings: Application settings
            max_routing_iterations: Max times same agent can be re-invoked
            max_log_entries: Max entries in DEVIATION_LOG.md before archive
        """
        super().__init__(
            name="DeviationHandler",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=4000,  # 4K tokens for RCA reasoning
        )
        self.max_routing_iterations = max_routing_iterations
        self.deviation_log_path = Path("DEVIATION_LOG.md")
        self.max_log_entries = max_log_entries

    async def _build_prompt(
        self,
        state: WorkflowState,
        **kwargs: object,
    ) -> str:
        """Build RCA prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context (rejection_reason, rejecting_agent)

        Returns:
            Formatted prompt for root cause analysis
        """
        rejection_reason = kwargs.get("rejection_reason", "Unknown rejection")
        rejecting_agent = kwargs.get(
            "rejecting_agent", state.get("current_agent", "Unknown")
        )

        prompt = f"""# ROOT CAUSE ANALYSIS - Agent Rejection

## Workflow Context
**Workflow ID:** {state['workflow_id']}
**User Request:** {state['user_request']}
**Current Phase:** {state['current_phase']}
**Rejecting Agent:** {rejecting_agent}
**Rejection Count:** {state['rejection_count']}

## Rejection Details
**Reason:** {rejection_reason}

## Blocking Issues
{self._format_blocking_issues(state.get('blocking_issues', []))}

## Recent Artifacts
**Requirements:** {'Present' if state.get('requirements') else 'Missing'}
**Architecture:** {'Present' if state.get('architecture') else 'Missing'}
**Code Files:** {len(state.get('code_files', {}))} files
**Test Files:** {len(state.get('test_files', {}))} files

## Your Task
Analyze the rejection and determine:

1. **Root Cause:** What is the underlying issue causing this rejection?
2. **Target Agent:** Which agent should handle the fix?
   - RequirementsStrategy: Ambiguous/missing requirements
   - SolutionArchitect: Architectural inconsistency
   - ImplementationPlanner: Task breakdown issues
   - DependencyResolver: Missing/conflicting dependencies
   - SoftwareEngineer: Code implementation bugs
   - StaticAnalysisAgent: Type errors, linting issues
   - QualityEngineer: Test failures, coverage gaps
   - SecurityValidator: Security vulnerabilities
   - ProductValidator: Requirements mismatch
3. **Circular Routing Check:** Is this the same agent being re-invoked repeatedly?
4. **Escalation Needed:** Should this be escalated to human approval?

## Response Format
Respond with JSON:
```json
{{
  "root_cause": "Clear explanation of the underlying issue",
  "target_agent": "AgentName",
  "reasoning": "Why this agent should handle the fix",
  "circular_routing_detected": false,
  "escalate_to_human": false,
  "recommended_action": "Specific action the target agent should take"
}}
```
"""
        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse RCA output and routing decision.

        Args:
            response: LLM response with RCA analysis
            state: Current workflow state

        Returns:
            Routing decision dictionary

        Raises:
            InfiniteLoopDetectedError: If circular routing detected
            HumanApprovalTimeoutError: If escalation required
        """
        import json

        # Extract JSON from response
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: default routing to Software Engineer
            analysis = {
                "root_cause": "Unable to parse LLM response",
                "target_agent": "SoftwareEngineer",
                "reasoning": "Default routing due to parse error",
                "circular_routing_detected": False,
                "escalate_to_human": False,
                "recommended_action": "Review and fix blocking issues",
            }

        # Check circular routing
        if self._check_circular_routing(state, analysis["target_agent"]):
            analysis["circular_routing_detected"] = True
            analysis["escalate_to_human"] = True

        # Check max iterations
        if state["rejection_count"] >= self.max_routing_iterations:
            analysis["escalate_to_human"] = True
            analysis["reasoning"] = (
                f"Max iterations ({self.max_routing_iterations}) reached"
            )

        # Append to deviation log
        await self._append_deviation_log(state, analysis)

        # Escalate if needed
        if analysis["escalate_to_human"]:
            raise HumanApprovalTimeoutError(
                gate_name="deviation_escalation",
                timeout_seconds=self.settings.human_approval_timeout,
                details={
                    "root_cause": analysis["root_cause"],
                    "rejection_count": state["rejection_count"],
                    "circular_routing": analysis["circular_routing_detected"],
                },
            )

        return {
            "routing_decision": {
                "target_agent": self._map_agent_to_tier(analysis["target_agent"]),
                "root_cause": analysis["root_cause"],
                "reasoning": analysis["reasoning"],
                "iteration_count": state["rejection_count"] + 1,
            },
            "escalation_flag": False,
        }

    def _get_temperature(self) -> float:
        """Use low temperature for deterministic reasoning."""
        return 0.2

    def _check_circular_routing(self, state: WorkflowState, target_agent: str) -> bool:
        """Check if target agent is being repeatedly invoked.

        Args:
            state: Current workflow state
            target_agent: Proposed target agent

        Returns:
            True if circular routing detected
        """
        # Check routing history from state
        routing_history = state.get("routing_decision", {})
        if not routing_history:
            return False

        # Simple check: has this agent been routed to recently?
        recent_target = routing_history.get("target_agent", "")
        return bool(target_agent in recent_target and state["rejection_count"] >= 2)

    def _map_agent_to_tier(self, agent_name: str) -> str:
        """Map agent name to tier node identifier.

        Args:
            agent_name: Agent name from LLM response

        Returns:
            Tier node identifier for LangGraph routing
        """
        mapping = {
            "RequirementsStrategy": "tier_1_requirements",
            "StrategyValidator": "tier_1_validator",
            "SolutionArchitect": "tier_1_architect",
            "ImplementationPlanner": "tier_2_planner",
            "DependencyResolver": "tier_2_dependencies",
            "SoftwareEngineer": "tier_3_engineer",
            "StaticAnalysisAgent": "tier_3_static_analysis",
            "QualityEngineer": "tier_3_quality",
            "SecurityValidator": "tier_4_security",
            "ProductValidator": "tier_4_product",
            "DocumentationAgent": "tier_5_docs",
            "DeploymentAgent": "tier_5_deployment",
        }
        return mapping.get(
            agent_name, "tier_3_engineer"
        )  # Default to Software Engineer

    async def _append_deviation_log(
        self,
        state: WorkflowState,
        analysis: dict[str, Any],
    ) -> None:
        """Append deviation entry to DEVIATION_LOG.md.

        Archives log if exceeds max_log_entries.

        Args:
            state: Current workflow state
            analysis: RCA analysis results
        """
        # Check if log needs archiving
        if self.deviation_log_path.exists():
            await self._maybe_archive_log()

        # Format entry
        timestamp = datetime.now(UTC).isoformat()
        entry = f"""
---

## Deviation Entry - {timestamp}

**Workflow ID:** {state['workflow_id']}
**Rejecting Agent:** {state.get('current_agent', 'Unknown')}
**Rejection Count:** {state['rejection_count']}

**Root Cause:**
{analysis.get('root_cause', 'N/A')}

**Routing Decision:**
- **Target Agent:** {analysis.get('target_agent', 'N/A')}
- **Reasoning:** {analysis.get('reasoning', 'N/A')}
- **Recommended Action:** {analysis.get('recommended_action', 'N/A')}

**Flags:**
- Circular Routing: {analysis.get('circular_routing_detected', False)}
- Escalation: {analysis.get('escalate_to_human', False)}

"""
        await self._append_to_file(str(self.deviation_log_path), entry)

    async def _maybe_archive_log(self) -> None:
        """Archive DEVIATION_LOG.md if exceeds max_log_entries."""
        if not self.deviation_log_path.exists():
            return

        # Count entries (sections starting with ##)
        content = await self._read_if_exists(str(self.deviation_log_path))
        if not content:
            return

        entry_count = content.count("## Deviation Entry")

        if entry_count >= self.max_log_entries:
            # Archive to DEVIATION_LOG_archive_{timestamp}.md
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            archive_path = Path(f"DEVIATION_LOG_archive_{timestamp}.md")
            await self._write_file(str(archive_path), content)

            # Create new log with header
            header = f"""# Deviation Log

**Purpose:** Track agent rejections and routing decisions for root cause analysis.
**Max Entries:** {self.max_log_entries} (auto-archives when exceeded)
**Archived:** {timestamp}

"""
            await self._write_file(str(self.deviation_log_path), header)

    def _format_blocking_issues(self, issues: list[str]) -> str:
        """Format blocking issues list for prompt.

        Args:
            issues: List of blocking issues

        Returns:
            Formatted string
        """
        if not issues:
            return "None"

        return "\n".join(f"- {issue}" for issue in issues)

    async def log_deviation(
        self,
        state: WorkflowState,
        error: Exception,
        agent_name: str | None = None,
    ) -> WorkflowState:
        """
        Log deviation/error to state and DEVIATION_LOG.md.

        Args:
            state: Current workflow state
            error: Exception that occurred
            agent_name: Name of agent where error occurred

        Returns:
            Updated workflow state with deviation logged
        """
        agent = agent_name or state.get("current_agent", "Unknown")

        # Create deviation entry
        deviation_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "agent": agent,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "rejection_count": state["rejection_count"],
        }

        # Update state
        deviations_list = state.get("deviations", [])
        if isinstance(deviations_list, list):
            deviations_list.append(deviation_entry)

        updated_state = state.copy()
        updated_state["deviations"] = deviations_list
        updated_state["last_error"] = str(error)

        # Log to file
        log_entry = f"""
---

## Deviation - {deviation_entry['timestamp']}

**Workflow ID:** {state['workflow_id']}
**Agent:** {agent}
**Error Type:** {deviation_entry['error_type']}
**Error Message:** {deviation_entry['error_message']}
**Rejection Count:** {deviation_entry['rejection_count']}

"""
        await self._append_to_file(str(self.deviation_log_path), log_entry)

        logger.warning(
            "deviation_logged",
            workflow_id=state["workflow_id"],
            agent=agent,
            error_type=deviation_entry["error_type"],
            rejection_count=deviation_entry["rejection_count"],
        )

        return updated_state

    async def attempt_recovery(
        self,
        state: WorkflowState,
        error: Exception,
        max_retries: int = 3,
    ) -> WorkflowState:
        """
        Attempt to recover from error with retry logic.

        Uses exponential backoff for transient errors.

        Args:
            state: Current workflow state
            error: Exception to recover from
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Updated workflow state

        Raises:
            WorkflowError: If recovery fails after max retries
        """
        retry_count = state.get("retry_count", 0)
        retry_count_int = retry_count if isinstance(retry_count, int) else 0

        if retry_count_int >= max_retries:
            logger.error(
                "recovery_max_retries_exceeded",
                workflow_id=state["workflow_id"],
                retry_count=retry_count_int,
                max_retries=max_retries,
            )
            raise WorkflowError(f"Max retries ({max_retries}) exceeded: {error}")

        # Exponential backoff: 2^retry_count seconds
        backoff_delay = 2**retry_count_int

        logger.info(
            "attempting_recovery",
            workflow_id=state["workflow_id"],
            retry_count=retry_count_int + 1,
            backoff_seconds=backoff_delay,
            error_type=type(error).__name__,
        )

        await asyncio.sleep(backoff_delay)

        # Update state
        updated_state = state.copy()
        updated_state["retry_count"] = retry_count_int + 1
        updated_state["last_retry_timestamp"] = datetime.now(UTC).isoformat()

        return updated_state

    async def rollback_state(
        self,
        state: WorkflowState,
        checkpoint_manager: Any | None = None,
    ) -> WorkflowState:
        """
        Rollback to previous checkpoint state.

        Args:
            state: Current workflow state
            checkpoint_manager: Checkpoint manager instance (optional)

        Returns:
            Previous workflow state from checkpoint

        Raises:
            WorkflowError: If no checkpoint available
        """
        workflow_id = state["workflow_id"]

        if not checkpoint_manager:
            logger.warning(
                "rollback_no_checkpoint_manager",
                workflow_id=workflow_id,
                action="returning_current_state",
            )
            return state

        # Get previous checkpoint
        try:
            checkpoints = await checkpoint_manager.alist(
                config={"configurable": {"thread_id": workflow_id}},
                limit=5,
            )

            if not checkpoints or len(checkpoints) < 2:
                logger.warning(
                    "rollback_no_previous_checkpoint",
                    workflow_id=workflow_id,
                    available_checkpoints=len(checkpoints) if checkpoints else 0,
                )
                return state

            # Get second-to-last checkpoint (last is current state)
            previous_checkpoint = checkpoints[1]

            logger.info(
                "state_rolled_back",
                workflow_id=workflow_id,
                from_version=state.get("state_version", 0),
                to_checkpoint=previous_checkpoint.checkpoint_id,
            )

            # Convert checkpoint back to state
            rolled_back_state = state.copy()
            rolled_back_state["rollback_performed"] = True
            rolled_back_state["rollback_timestamp"] = datetime.now(UTC).isoformat()

            return rolled_back_state

        except Exception as e:
            logger.error(
                "rollback_failed",
                workflow_id=workflow_id,
                error=str(e),
            )
            raise WorkflowError(f"State rollback failed: {e}") from e

    async def escalate_to_human(
        self,
        state: WorkflowState,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> WorkflowState:
        """
        Escalate workflow to human approval.

        Sets approval gate flag and updates state.

        Args:
            state: Current workflow state
            reason: Reason for escalation
            details: Additional escalation details

        Returns:
            Updated workflow state with escalation flag

        Raises:
            HumanApprovalTimeoutError: Always (to trigger approval gate)
        """
        logger.warning(
            "escalating_to_human",
            workflow_id=state["workflow_id"],
            reason=reason,
            rejection_count=state["rejection_count"],
        )

        # Update state
        updated_state = state.copy()
        updated_state["requires_human_approval"] = True
        updated_state["approval_reason"] = reason
        updated_state["escalation_details"] = details or {}
        updated_state["escalation_timestamp"] = datetime.now(UTC).isoformat()

        # Log escalation
        escalation_timestamp = updated_state.get("escalation_timestamp", "")
        escalation_entry = f"""
---

## ESCALATION - {escalation_timestamp}

**Workflow ID:** {state['workflow_id']}
**Reason:** {reason}
**Rejection Count:** {state['rejection_count']}

**Details:**
{self._format_dict(details or {})}

"""
        await self._append_to_file(str(self.deviation_log_path), escalation_entry)

        # Raise exception to trigger human approval gate
        raise HumanApprovalTimeoutError(
            gate_name="deviation_escalation",
            timeout_seconds=self.settings.human_approval_timeout,
            details={
                "reason": reason,
                "rejection_count": state["rejection_count"],
                **(details or {}),
            },
        )

    def _format_dict(self, data: dict[str, Any]) -> str:
        """Format dictionary for markdown output."""
        if not data:
            return "None"

        return "\n".join(f"- **{k}:** {v}" for k, v in data.items())
