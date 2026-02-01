"""Phase 5 Agent Usage Examples.

This module demonstrates how to use the three Tier 3 agents:
- SoftwareEngineerAgent
- StaticAnalysisAgent
- QualityEngineerAgent
"""

from __future__ import annotations

import asyncio

from src.agents.tier_3 import (
    QualityEngineerAgent,
    SoftwareEngineerAgent,
    StaticAnalysisAgent,
)
from src.config import Settings
from src.llm.openrouter_client import OpenRouterClient
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


async def example_software_engineer_usage() -> None:
    """Example: Using Software Engineer Agent to generate code."""
    # Setup
    settings = Settings()
    llm_client = OpenRouterClient(settings)
    budget_guard = BudgetGuard(settings)

    # Create agent
    software_engineer = SoftwareEngineerAgent(
        name="SoftwareEngineerAgent",
        llm_client=llm_client,
        budget_guard=budget_guard,
        settings=settings,
        token_budget=16000,  # Highest allocation
    )

    # Initial state
    state: WorkflowState = {
        "workflow_id": "example-001",
        "current_task_id": "TASK-025",
        "current_phase": "development",
        "rejection_count": 0,
        "tokens_used": 0,
        "cost_usd": 0.0,
    }

    # Execute agent
    print("Executing Software Engineer Agent...")
    updated_state = await software_engineer.execute(state)

    # Check results
    files_created = updated_state.get("partial_artifacts", {}).get("files_created", [])
    print(f"Files created: {files_created}")
    print(f"Status: {updated_state.get('partial_artifacts', {}).get('status')}")


async def example_static_analysis_usage() -> None:
    """Example: Using Static Analysis Agent to validate code."""
    # Setup
    settings = Settings()
    llm_client = OpenRouterClient(settings)  # Uses Gemini-2.5-Flash
    budget_guard = BudgetGuard(settings)

    # Create agent
    static_analysis = StaticAnalysisAgent(
        name="StaticAnalysisAgent",
        llm_client=llm_client,
        budget_guard=budget_guard,
        settings=settings,
        token_budget=2000,
    )

    # State after Software Engineer
    state: WorkflowState = {
        "workflow_id": "example-001",
        "current_phase": "development",
        "rejection_count": 0,
        "tokens_used": 16000,
        "cost_usd": 0.016,
    }

    # Execute agent (will run black, ruff, mypy, radon)
    print("Executing Static Analysis Agent...")
    updated_state = await static_analysis.execute(state)

    # Check results
    status = updated_state.get("partial_artifacts", {}).get("status")
    critical_issues = updated_state.get("partial_artifacts", {}).get(
        "critical_issues", []
    )

    print(f"Status: {status}")
    print(f"Critical Issues: {critical_issues}")

    if status == "REJECTED":
        print("Code rejected. Routing back to Software Engineer with feedback.")
        # Read COMPLIANCE_LOG.md for detailed feedback
    else:
        print("Code approved. Proceeding to Quality Engineer.")


async def example_quality_engineer_usage() -> None:
    """Example: Using Quality Engineer Agent to generate and run tests."""
    # Setup
    settings = Settings()
    llm_client = OpenRouterClient(settings)  # Uses DeepSeek-V3.2
    budget_guard = BudgetGuard(settings)

    # Create agent
    quality_engineer = QualityEngineerAgent(
        name="QualityEngineerAgent",
        llm_client=llm_client,
        budget_guard=budget_guard,
        settings=settings,
        token_budget=12000,
    )

    # State after Static Analysis approval
    state: WorkflowState = {
        "workflow_id": "example-001",
        "current_phase": "development",
        "rejection_count": 0,
        "tokens_used": 18000,
        "cost_usd": 0.018,
    }

    # Execute agent (will generate tests and run pytest)
    print("Executing Quality Engineer Agent...")
    updated_state = await quality_engineer.execute(state)

    # Check results
    files_created = updated_state.get("partial_artifacts", {}).get("files_created", [])
    coverage = updated_state.get("partial_artifacts", {}).get("coverage_percent", 0.0)
    status = updated_state.get("partial_artifacts", {}).get("status")

    print(f"Test files created: {files_created}")
    print(f"Coverage: {coverage:.1f}%")
    print(f"Status: {status}")

    if status == "REJECTED":
        print("Tests failed or coverage below threshold.")
        print("Routing to Software Engineer (fix bugs) or Quality Engineer (fix tests)")
    else:
        print("Tests passed. Proceeding to Tier 4 (Security Validator).")


async def example_full_tier_3_workflow() -> None:
    """Example: Complete Tier 3 workflow with all three agents."""
    # Setup
    settings = Settings()
    llm_client_deepseek = OpenRouterClient(settings)  # For Software Engineer & QE
    llm_client_gemini = OpenRouterClient(settings)  # For Static Analysis
    budget_guard = BudgetGuard(settings)

    # Create agents
    software_engineer = SoftwareEngineerAgent(
        name="SoftwareEngineerAgent",
        llm_client=llm_client_deepseek,
        budget_guard=budget_guard,
        settings=settings,
        token_budget=16000,
    )

    static_analysis = StaticAnalysisAgent(
        name="StaticAnalysisAgent",
        llm_client=llm_client_gemini,
        budget_guard=budget_guard,
        settings=settings,
        token_budget=2000,
    )

    quality_engineer = QualityEngineerAgent(
        name="QualityEngineerAgent",
        llm_client=llm_client_deepseek,
        budget_guard=budget_guard,
        settings=settings,
        token_budget=12000,
    )

    # Initial state
    state: WorkflowState = {
        "workflow_id": "example-full-001",
        "current_task_id": "TASK-025",
        "current_phase": "development",
        "rejection_count": 0,
        "tokens_used": 0,
        "cost_usd": 0.0,
    }

    max_iterations = 3  # Prevent infinite loops

    for iteration in range(max_iterations):
        print(f"\n=== Iteration {iteration + 1} ===")

        # Step 1: Software Engineer generates code
        print("1. Software Engineer: Generating code...")
        state = await software_engineer.execute(state)

        # Step 2: Static Analysis validates code
        print("2. Static Analysis: Validating code quality...")
        state = await static_analysis.execute(state)

        static_status = state.get("partial_artifacts", {}).get("status")
        if static_status == "REJECTED":
            print("   ❌ Static Analysis REJECTED. Fixing issues...")
            state["feedback"] = "See COMPLIANCE_LOG.md for details"
            state["rejected_by"] = "StaticAnalysisAgent"
            state["rejection_count"] = state.get("rejection_count", 0) + 1
            continue  # Retry with Software Engineer

        print("   ✅ Static Analysis APPROVED")

        # Step 3: Quality Engineer generates and runs tests
        print("3. Quality Engineer: Generating and running tests...")
        state = await quality_engineer.execute(state)

        quality_status = state.get("partial_artifacts", {}).get("status")
        if quality_status == "REJECTED":
            print("   ❌ Quality Engineer REJECTED. Fixing bugs...")
            state["feedback"] = "See QUALITY_REPORT.md for details"
            state["rejected_by"] = "QualityEngineerAgent"
            state["rejection_count"] = state.get("rejection_count", 0) + 1
            continue  # Retry with Software Engineer

        print("   ✅ Quality Engineer APPROVED")
        print("\n🎉 Tier 3 workflow completed successfully!")
        break
    else:
        print(f"\n⚠️ Max iterations ({max_iterations}) reached. Escalating to human.")


async def main() -> None:
    """Run all examples."""
    print("=== Phase 5 Agent Usage Examples ===\n")

    # Example 1: Software Engineer
    print("\n--- Example 1: Software Engineer Agent ---")
    await example_software_engineer_usage()

    # Example 2: Static Analysis
    print("\n--- Example 2: Static Analysis Agent ---")
    await example_static_analysis_usage()

    # Example 3: Quality Engineer
    print("\n--- Example 3: Quality Engineer Agent ---")
    await example_quality_engineer_usage()

    # Example 4: Full Tier 3 Workflow
    print("\n--- Example 4: Full Tier 3 Workflow ---")
    await example_full_tier_3_workflow()


if __name__ == "__main__":
    asyncio.run(main())
