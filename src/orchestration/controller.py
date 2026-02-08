"""Orchestration controller with LangGraph StateGraph coordination.

Main entry point for workflow execution across 6 tiers.
Implements tier routing, quality gates, and budget enforcement.
"""

from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.config import Settings
from src.exceptions import (
    BudgetExhaustedError,
    InfiniteLoopDetectedError,
)
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.checkpoints import CheckpointManager
from src.orchestration.state import WorkflowState


class OrchestrationController:
    """LangGraph StateGraph coordinator for multi-tier workflow.

    Orchestrates 6-tier agent workflow:
    - Tier 0: Control & Governance
    - Tier 1: Planning & Strategy
    - Tier 2: Preparation
    - Tier 3: Development
    - Tier 4: Validation & Security
    - Tier 5: Integration & Delivery

    Attributes:
        settings: Application settings
        budget_guard: Budget enforcement
        checkpoint_manager: Checkpoint persistence
        graph: LangGraph StateGraph
        max_iterations: Maximum workflow iterations (default: 50)
    """

    def __init__(
        self,
        settings: Settings,
        budget_guard: BudgetGuard,
        checkpoint_manager: CheckpointManager,
        max_iterations: int = 50,
    ) -> None:
        """Initialize orchestration controller.

        Args:
            settings: Application settings
            budget_guard: Budget guard instance
            checkpoint_manager: Checkpoint manager instance
            max_iterations: Maximum workflow iterations before timeout
        """
        self.settings = settings
        self.budget_guard = budget_guard
        self.checkpoint_manager = checkpoint_manager
        self.max_iterations = max_iterations
        self.graph: CompiledStateGraph | None = None

    def build_graph(self) -> CompiledStateGraph:
        """Build LangGraph StateGraph with tier nodes and routing.

        Creates workflow graph with:
        - Tier 0-5 nodes
        - Conditional edges for routing (pass/reject/escalate)
        - Budget enforcement
        - Quality gates

        Returns:
            Configured StateGraph instance
        """
        # Create graph with WorkflowState schema
        graph = StateGraph(WorkflowState)

        # Add tier nodes
        graph.add_node("tier_0_deviation", self._tier_0_deviation_handler)
        graph.add_node("tier_1_requirements", self._tier_1_requirements)
        graph.add_node("tier_1_validator", self._tier_1_validator)
        graph.add_node("tier_1_architect", self._tier_1_architect)
        graph.add_node("tier_2_planner", self._tier_2_planner)
        graph.add_node("tier_2_dependencies", self._tier_2_dependencies)
        graph.add_node("tier_3_engineer", self._tier_3_engineer)
        graph.add_node("tier_3_static_analysis", self._tier_3_static_analysis)
        graph.add_node("tier_3_quality", self._tier_3_quality)
        graph.add_node("tier_4_security", self._tier_4_security)
        graph.add_node("tier_4_product", self._tier_4_product)
        graph.add_node("tier_5_docs", self._tier_5_docs)
        graph.add_node("tier_5_deployment", self._tier_5_deployment)

        # Set entry point
        graph.set_entry_point("tier_1_requirements")

        # Add conditional edges (routing logic)
        self._add_conditional_edges(graph)

        # Set finish point
        graph.add_edge("tier_5_deployment", END)

        self.graph = graph.compile(checkpointer=self.checkpoint_manager)
        return self.graph

    def _add_conditional_edges(self, graph: StateGraph) -> None:
        """Add conditional routing edges to graph.

        Implements quality gate logic:
        - PASS → Next tier
        - REJECT → Deviation Handler
        - ESCALATE → Human approval

        Args:
            graph: StateGraph instance to modify
        """
        # Tier 1: Requirements → Validator
        graph.add_edge("tier_1_requirements", "tier_1_validator")

        # Tier 1: Validator → Architect or Deviation
        graph.add_conditional_edges(
            "tier_1_validator",
            self._route_validator_output,
            {
                "tier_1_architect": "tier_1_architect",
                "tier_0_deviation": "tier_0_deviation",
                END: END,
            },
        )

        # Tier 1: Architect → Planner
        graph.add_edge("tier_1_architect", "tier_2_planner")

        # Tier 2: Planner → Dependencies
        graph.add_edge("tier_2_planner", "tier_2_dependencies")

        # Tier 2: Dependencies → Engineer or Deviation
        graph.add_conditional_edges(
            "tier_2_dependencies",
            self._route_dependencies_output,
            {
                "tier_3_engineer": "tier_3_engineer",
                "tier_0_deviation": "tier_0_deviation",
                END: END,
            },
        )

        # Tier 3: Engineer → Static Analysis
        graph.add_edge("tier_3_engineer", "tier_3_static_analysis")

        # Tier 3: Static Analysis → Quality or Deviation
        graph.add_conditional_edges(
            "tier_3_static_analysis",
            self._route_static_analysis_output,
            {
                "tier_3_quality": "tier_3_quality",
                "tier_0_deviation": "tier_0_deviation",
                END: END,
            },
        )

        # Tier 3: Quality → Security or Deviation
        graph.add_conditional_edges(
            "tier_3_quality",
            self._route_quality_output,
            {
                "tier_4_security": "tier_4_security",
                "tier_0_deviation": "tier_0_deviation",
                END: END,
            },
        )

        # Tier 4: Security → Product or Deviation
        graph.add_conditional_edges(
            "tier_4_security",
            self._route_security_output,
            {
                "tier_4_product": "tier_4_product",
                "tier_0_deviation": "tier_0_deviation",
                END: END,
            },
        )

        # Tier 4: Product → Docs or Deviation
        graph.add_conditional_edges(
            "tier_4_product",
            self._route_product_output,
            {
                "tier_5_docs": "tier_5_docs",
                "tier_0_deviation": "tier_0_deviation",
                END: END,
            },
        )

        # Tier 5: Docs → Deployment
        graph.add_edge("tier_5_docs", "tier_5_deployment")

        # Tier 0: Deviation Handler → Routed Agent
        graph.add_conditional_edges(
            "tier_0_deviation",
            self._route_deviation_output,
            {
                # Can route to any tier
                "tier_1_requirements": "tier_1_requirements",
                "tier_1_architect": "tier_1_architect",
                "tier_2_planner": "tier_2_planner",
                "tier_3_engineer": "tier_3_engineer",
                "tier_3_static_analysis": "tier_3_static_analysis",
                "tier_4_security": "tier_4_security",
                END: END,
            },
        )

    async def execute_workflow(
        self,
        user_request: str,
        workflow_id: str,
    ) -> WorkflowState:
        """Execute complete workflow from user request.

        Args:
            user_request: User's original request
            workflow_id: Unique workflow identifier

        Returns:
            Final workflow state

        Raises:
            BudgetExhaustedError: If budget limits exceeded
            InfiniteLoopDetectedError: If max iterations reached
        """
        if not self.graph:
            self.build_graph()

        # Initialize workflow state
        initial_state: WorkflowState = {
            "workflow_id": workflow_id,
            "user_request": user_request,
            "current_phase": "planning",
            "current_task": "requirements_analysis",
            "current_agent": "OrchestrationController",
            "rejection_count": 0,
            "state_version": 1,
            "requirements": "",
            "architecture": "",
            "tasks": "",
            "code_files": {},
            "test_files": {},
            "partial_artifacts": {},
            "validation_report": "",
            "quality_report": "",
            "security_report": "",
            "budget_used_tokens": 0,
            "budget_used_usd": 0.0,
            "budget_remaining_tokens": self.settings.total_budget_tokens,
            "budget_remaining_usd": self.settings.max_monthly_budget_usd,
            "quality_gates_passed": [],
            "blocking_issues": [],
            "awaiting_human_approval": False,
            "approval_gate": "",
            "approval_timeout": "",
            "routing_decision": {},
            "escalation_flag": False,
            "trace_id": workflow_id,
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Execute workflow
        config: RunnableConfig = {"configurable": {"workflow_id": workflow_id}}
        final_state = initial_state

        if self.graph is None:
            raise RuntimeError("Graph not compiled")

        iteration = 0
        async for state_update in self.graph.astream(initial_state, config):
            # Extract the actual state from the update
            if isinstance(state_update, dict):
                # Get the last key's value which contains the state
                for key_val in state_update.values():
                    if isinstance(key_val, dict) and "workflow_id" in key_val:
                        final_state = key_val  # type: ignore[assignment]
                        break
            iteration += 1

            # Check budget
            if final_state["budget_remaining_tokens"] <= 0:
                raise BudgetExhaustedError(
                    budget_type="tokens",
                    limit=self.settings.total_budget_tokens,
                    requested=final_state["budget_used_tokens"],
                )

            # Check iterations
            if iteration >= self.max_iterations:
                raise InfiniteLoopDetectedError(
                    agent_name=final_state["current_agent"],
                    max_iterations=self.max_iterations,
                    current_state=final_state["current_phase"],
                )

        return final_state

    # Tier node implementations (stubs for Phase 2)
    # Full implementations will be added in Phase 3

    async def _tier_0_deviation_handler(self, state: WorkflowState) -> WorkflowState:
        """Tier 0: Deviation Handler node (stub)."""
        state["current_agent"] = "DeviationHandler"
        return state

    async def _tier_1_requirements(self, state: WorkflowState) -> WorkflowState:
        """Tier 1: Requirements & Strategy node (stub)."""
        state["current_agent"] = "RequirementsStrategy"
        state["current_phase"] = "planning"
        return state

    async def _tier_1_validator(self, state: WorkflowState) -> WorkflowState:
        """Tier 1: Strategy Validator node (stub)."""
        state["current_agent"] = "StrategyValidator"
        return state

    async def _tier_1_architect(self, state: WorkflowState) -> WorkflowState:
        """Tier 1: Solution Architect node (stub)."""
        state["current_agent"] = "SolutionArchitect"
        return state

    async def _tier_2_planner(self, state: WorkflowState) -> WorkflowState:
        """Tier 2: Implementation Planner node (stub)."""
        state["current_agent"] = "ImplementationPlanner"
        state["current_phase"] = "preparation"
        return state

    async def _tier_2_dependencies(self, state: WorkflowState) -> WorkflowState:
        """Tier 2: Dependency Resolver node (stub)."""
        state["current_agent"] = "DependencyResolver"
        return state

    async def _tier_3_engineer(self, state: WorkflowState) -> WorkflowState:
        """Tier 3: Software Engineer node (stub)."""
        state["current_agent"] = "SoftwareEngineer"
        state["current_phase"] = "development"
        return state

    async def _tier_3_static_analysis(self, state: WorkflowState) -> WorkflowState:
        """Tier 3: Static Analysis node (stub)."""
        state["current_agent"] = "StaticAnalysisAgent"
        return state

    async def _tier_3_quality(self, state: WorkflowState) -> WorkflowState:
        """Tier 3: Quality Engineer node (stub)."""
        state["current_agent"] = "QualityEngineer"
        return state

    async def _tier_4_security(self, state: WorkflowState) -> WorkflowState:
        """Tier 4: Security Validator node (stub)."""
        state["current_agent"] = "SecurityValidator"
        state["current_phase"] = "validation"
        return state

    async def _tier_4_product(self, state: WorkflowState) -> WorkflowState:
        """Tier 4: Product Validator node (stub)."""
        state["current_agent"] = "ProductValidator"
        return state

    async def _tier_5_docs(self, state: WorkflowState) -> WorkflowState:
        """Tier 5: Documentation Agent node (stub)."""
        state["current_agent"] = "DocumentationAgent"
        state["current_phase"] = "delivery"
        return state

    async def _tier_5_deployment(self, state: WorkflowState) -> WorkflowState:
        """Tier 5: Deployment Agent node (stub)."""
        state["current_agent"] = "DeploymentAgent"
        state["current_phase"] = "completed"
        return state

    # Routing functions (stubs for Phase 2)
    # Full logic will be added in Phase 3

    def _route_validator_output(self, state: WorkflowState) -> str:
        """Route Strategy Validator output."""
        if state.get("blocking_issues"):
            return "tier_0_deviation"
        return "tier_1_architect"

    def _route_dependencies_output(self, state: WorkflowState) -> str:
        """Route Dependency Resolver output."""
        if state.get("blocking_issues"):
            return "tier_0_deviation"
        return "tier_3_engineer"

    def _route_static_analysis_output(self, state: WorkflowState) -> str:
        """Route Static Analysis output."""
        if state.get("blocking_issues"):
            return "tier_0_deviation"
        return "tier_3_quality"

    def _route_quality_output(self, state: WorkflowState) -> str:
        """Route Quality Engineer output."""
        if state.get("blocking_issues"):
            return "tier_0_deviation"
        return "tier_4_security"

    def _route_security_output(self, state: WorkflowState) -> str:
        """Route Security Validator output."""
        if state.get("blocking_issues"):
            return "tier_0_deviation"
        return "tier_4_product"

    def _route_product_output(self, state: WorkflowState) -> str:
        """Route Product Validator output."""
        if state.get("blocking_issues"):
            return "tier_0_deviation"
        return "tier_5_docs"

    def _route_deviation_output(self, state: WorkflowState) -> str:
        """Route Deviation Handler output to target agent."""
        routing = state.get("routing_decision", {})
        target_agent = routing.get("target_agent", "tier_1_requirements")

        # Check for escalation or max iterations
        if state.get("escalation_flag") or state["rejection_count"] >= 3:
            return END

        return target_agent
