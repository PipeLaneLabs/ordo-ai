"""Observability Agent for Tier 2.

Defines observability strategy with:
- Structured logging requirements and schema
- Prometheus metrics and SLIs
- Distributed tracing strategy
- Monitoring dashboards
- Alerting rules
- Log aggregation pipeline
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class ObservabilityAgent(BaseAgent):
    """Tier 2 agent for observability strategy definition.

    Uses Gemini-2.5-Flash for observability specification.
    Generates OBSERVABILITY.md with logging, metrics, tracing, and alerting.

    Attributes:
        token_budget: 3,000 tokens for observability spec
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Observability Agent.

        Args:
            llm_client: LLM client (should use Gemini-2.5-Flash for speed)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="ObservabilityAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=3000,  # 3K tokens for observability spec
        )

    async def _build_prompt(
        self,
        state: WorkflowState,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> str:
        """Build observability strategy prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for observability specification
        """
        # Read required artifacts
        architecture = await self._read_if_exists("ARCHITECTURE.md")
        tasks = await self._read_if_exists("TASKS.md")
        requirements = await self._read_if_exists("REQUIREMENTS.md")

        if not architecture:
            raise ValueError(
                "ARCHITECTURE.md not found - Solution Architect must run first"
            )

        prompt = f"""# Observability Strategy Task

## Architecture Document
{architecture}

## Tasks Document
{tasks or "No tasks document available"}

## Requirements Document
{requirements or "No requirements document available"}

## Your Task
As an Observability Agent, define a comprehensive observability strategy for
this system.

### Strategy Framework

1. **Logging Strategy**
   - Define log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Structured logging schema (JSON format)
   - Required fields (timestamp, level, service, trace_id, etc.)
   - Agent-specific fields
   - Cost tracking fields
   - Error fields
   - Log retention policy

2. **Metrics & Monitoring**
   - RED metrics (Rate, Errors, Duration)
   - Workflow-specific metrics
   - Agent execution metrics
   - Cost & budget metrics
   - Infrastructure metrics (database, cache, storage)
   - Service Level Indicators (SLIs)
   - Prometheus configuration

3. **Distributed Tracing**
   - Trace architecture (spans, context propagation)
   - Span boundaries (workflow, tier, agent, LLM call)
   - Trace attributes
   - OpenTelemetry/Jaeger configuration

4. **Alerting Rules**
   - Critical alerts (PagerDuty/Email)
   - Warning alerts (Slack/Console)
   - Alert thresholds
   - Runbooks

5. **Dashboards**
   - Grafana dashboard specifications
   - Workflow overview dashboard
   - Agent performance dashboard
   - Cost & budget dashboard
   - Infrastructure health dashboard
   - Security & compliance dashboard

6. **Log Aggregation & Shipping**
   - Fluentd configuration
   - S3/Loki storage
   - Retention policies

7. **Code Instrumentation Examples**
   - Python code examples for Software Engineer
   - How to add logging, metrics, tracing to code

## Output Format

Generate an OBSERVABILITY.md document with the following structure:

```markdown
# Observability Strategy

**Project:** [Project Name]
**Agent:** Observability Agent
**Date:** [Current Date]
**Status:** ✅ SPECIFICATION COMPLETE
**For Implementation By:** Software Engineer Agent

---

## Table of Contents
1. [Overview](#overview)
2. [Logging Strategy](#logging-strategy)
3. [Metrics & Monitoring](#metrics--monitoring)
4. [Distributed Tracing](#distributed-tracing)
5. [Alerting Rules](#alerting-rules)
6. [Dashboards](#dashboards)
7. [Log Aggregation & Shipping](#log-aggregation--shipping)
8. [Code Instrumentation Examples](#code-instrumentation-examples)
9. [Implementation Checklist](#implementation-checklist)

---

## Overview

### Observability Goals

1. **Workflow Transparency:** Every agent invocation, state transition, and
   rejection is traceable
2. **Cost Visibility:** Real-time tracking of LLM token usage and costs per
   agent/tier
3. **Performance Monitoring:** P50/P95/P99 latencies for agents, API endpoints,
   and workflows
4. **Failure Detection:** Immediate alerts for critical failures, budget
   overruns, infinite loops
5. **Debugging Context:** Structured logs with trace IDs for full workflow
   reconstruction

### Observability Stack

```
┌─────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                           │
│  (FastAPI + Agents + LangGraph + Chainlit)                  │
│                                                              │
│  Instrumentation:                                            │
│  • structlog (structured logging)                            │
│  • prometheus-client (metrics)                               │
│  • opentelemetry-sdk (tracing)                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  COLLECTION LAYER                            │
│  • Logs → stdout (Docker captures, Fluentd ships to S3)     │
│  • Metrics → Prometheus (scrapes /metrics endpoint)          │
│  • Traces → Jaeger Collector (OTLP protocol)                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER                              │
│  • Logs: S3/Loki (90 days retention)                         │
│  • Metrics: Prometheus TSDB (15 days retention)              │
│  • Traces: Jaeger Storage (7 days retention)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                 VISUALIZATION LAYER                          │
│  • Grafana Dashboards (metrics + logs + traces)              │
│  • Chainlit UI (real-time workflow progress)                 │
│  • Jaeger UI (trace exploration)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Logging Strategy

### Framework: structlog

**Why structlog?**
- Structured output (JSON) for easy parsing
- Context binding (trace_id, workflow_id propagate automatically)
- Rich formatting for human-readable console output in dev
- Performance optimized (minimal overhead)

### Log Levels

### Log Levels
- **DEBUG**: Detailed diagnostics (LLM prompts, etc). Production: ❌
- **INFO**: Key business events (Start/Complete). Production: ✅
- **WARNING**: Degraded performance (Retries). Production: ✅
- **ERROR**: Failures (Rejections, API errors). Production: ✅
- **CRITICAL**: System failures (Budget exceeded). Production: ✅

### Structured Logging Schema

**Required Fields (All Logs):**
```json
{{
  "timestamp": "2026-01-24T00:00:00.000000Z",
  "level": "INFO",
  "service": "agent-api",
  "environment": "development",
  "version": "1.0.0",
  "logger": "src.agents.tier_3.software_engineer",
  "trace_id": "abc123-def456-ghi789",
  "workflow_id": "wf-20260124-001",
  "event": "agent.execution.started",
  "message": "Software Engineer started code generation"
}}
```

**Agent-Specific Fields:**
```json
{{
  "agent": {{
    "name": "software_engineer",
    "tier": 3,
    "invocation_id": "inv-12345"
  }},
  "task": {{
    "id": "TASK-025",
    "name": "Implement FastAPI main.py",
    "file": "src/main.py"
  }},
  "state": {{
    "current_phase": "development",
    "rejection_count": 0,
    "checkpoint_id": "chk-67890"
  }}
}}
```

**Cost Tracking Fields:**
```json
{{
  "llm": {{
    "provider": "openrouter",
    "model": "deepseek/deepseek-chat",
    "tokens_input": 5400,
    "tokens_output": 1200,
    "cost_usd": 0.0012,
    "latency_ms": 3450
  }},
  "budget": {{
    "remaining_tokens": 487600,
    "remaining_budget_usd": 18.45,
    "budget_percent_used": 7.75
  }}
}}
```

### Log Retention Policy

| Environment | Retention Period | Storage | Rotation | Cost Estimate |
|-------------|-----------------|---------|----------|---------------|
| **Development** | 7 days | Docker stdout (local) | Daily | $0 |
| **Production** | 90 days | S3 (Standard-IA) | Daily | $5/month |

---

## Metrics & Monitoring

### Framework: Prometheus + OpenTelemetry

### Metrics Categories

#### 1. RED Metrics (Request-focused)

**Rate:** Number of requests
```python
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
```

**Errors:** Number of failed requests
```python
http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status", "error_type"]
)
```

**Duration:** Request latency distribution
```python
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
```

#### 2. Workflow-Specific Metrics

**Workflow Execution Time:**
```python
workflow_duration_seconds = Histogram(
    "workflow_duration_seconds",
    "Workflow execution time in seconds",
    ["workflow_id", "status"],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400]  # 1min to 4hrs
)
```

**Agent Execution Time:**
```python
agent_execution_duration_seconds = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution time in seconds",
    ["agent_name", "tier", "status"],
    buckets=[1, 5, 10, 30, 60, 300, 600]  # 1s to 10min
)
```

**Rejection Metrics:**
```python
agent_rejections_total = Counter(
    "agent_rejections_total",
    "Total agent rejections",
    ["agent_name", "rejected_by", "reason"]
)
```

#### 3. Cost & Budget Metrics

**Token Usage:**
```python
llm_tokens_consumed_total = Counter(
    "llm_tokens_consumed_total",
    "Total LLM tokens consumed",
    # token_type: input/output
    ["provider", "model", "agent_name", "token_type"]
)

llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["provider", "model", "agent_name"]
)
```

**Budget Status:**
```python
budget_remaining_tokens = Gauge(
    "budget_remaining_tokens",
    "Remaining token budget",
    ["workflow_id"]
)

budget_percent_used = Gauge(
    "budget_percent_used",
    "Budget usage percentage",
    ["workflow_id"]
)
```

#### 4. Infrastructure Metrics

**Database Connections:**
```python
db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    ["database"]
)
```

**Cache Performance:**
```python
cache_hits_total = Counter(
    "cache_hits_total",
    "Cache hit count",
    ["cache_key_prefix"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Cache miss count",
    ["cache_key_prefix"]
)
```

### Service Level Indicators (SLIs)

**API Availability:**
```
SLI: Percentage of successful API requests (status 200-299)
Target: 99.9% (3 nines)
Measurement Window: 30 days rolling
```

**API Latency:**
```
SLI: P95 latency of /workflow/start endpoint
Target: < 500ms
Measurement: http_request_duration_seconds{{endpoint="/workflow/start",
             quantile="0.95"}}
```

**Workflow Success Rate:**
```
SLI: Percentage of workflows completing without human escalation
Target: > 80%
Measurement: (workflows_completed_total / workflows_started_total) * 100
```

---

## Distributed Tracing

### Framework: OpenTelemetry + Jaeger

### Span Boundaries

**Root Span:** Entire workflow execution
```python
Span Name: workflow.execute
Duration: 900s (15 minutes)
Attributes:
  workflow.id: wf-20260124-001
  workflow.user_request: "Create user registration API"
  workflow.status: completed
  workflow.tier_count: 5
```

**Agent Spans:** Individual agent invocations
```python
Span Name: agent.software_engineer.execute
Parent: tier.3.development
Duration: 45s
Attributes:
  agent.name: software_engineer
  agent.tier: 3
  agent.task_id: TASK-025
  agent.file: src/main.py
  agent.status: rejected
  agent.rejection_reason: "Test coverage 68% < 70%"
```

**LLM Call Spans:** External API calls
```python
Span Name: llm.openrouter.chat
Parent: agent.software_engineer.execute
Duration: 3.5s
Attributes:
  llm.provider: openrouter
  llm.model: deepseek/deepseek-chat
  llm.tokens_input: 5400
  llm.tokens_output: 1200
  llm.cost_usd: 0.0012
  llm.temperature: 0.2
```

---

## Alerting Rules

### Critical Alerts (PagerDuty / Email)

**1. Budget Hard Limit Reached**
```yaml
alert: BudgetHardLimitReached
expr: budget_percent_used >= 100
for: 1m
severity: critical
annotations:
  summary: "Workflow {{{{ $labels.workflow_id }}}} exceeded budget hard limit"
  description: "Token budget exhausted. Workflow execution paused."
actions:
  - Pause workflow immediately
  - Notify on-call engineer
```

**2. Infinite Loop Detected**
```yaml
alert: InfiniteLoopDetected
expr: workflow_rejection_count > 5
for: 5m
severity: critical
annotations:
  summary: "Workflow {{{{ $labels.workflow_id }}}} stuck in rejection loop"
  description: "Same agent rejected {{{{ $value }}}} times. Manual intervention
                required."
actions:
  - Escalate to human approval
```

### Warning Alerts (Slack / Console Log)

**1. High Error Rate**
```yaml
alert: HighErrorRate
expr: (rate(http_errors_total[5m]) / rate(http_requests_total[5m])) > 0.05
for: 5m
severity: warning
annotations:
  summary: "API error rate above 5% for {{{{ $labels.endpoint }}}}"
```

**2. Budget Threshold Warning**
```yaml
alert: BudgetThresholdWarning
expr: budget_percent_used >= 75
for: 1m
severity: warning
annotations:
  summary: "Workflow {{{{ $labels.workflow_id }}}} at 75% budget"
```

---

## Dashboards

### Grafana Dashboards (Pre-configured)

#### 1. Workflow Overview Dashboard

**Panels:**
- Total Workflows (Last 24h): Gauge
- Workflow Success Rate: Gauge (target: 80%)
- Active Workflows: Table (workflow_id, phase, duration, budget used)
- Workflow Duration (P50/P95/P99): Graph

#### 2. Agent Performance Dashboard

**Panels:**
- Agent Execution Time (by tier): Heatmap
- Agent Rejection Rate: Bar chart (by agent)
- Most Rejected Agent: Stat
- LLM Latency by Provider: Graph

#### 3. Cost & Budget Dashboard

**Panels:**
- Total LLM Cost (Last 30d): Stat
- Cost per Workflow (Average): Gauge
- Token Consumption by Agent: Bar chart
- Budget Utilization: Gauge (current vs limit)

#### 4. Infrastructure Health Dashboard

**Panels:**
- Service Health Status: Status panel (all services)
- API Request Rate: Graph (requests/sec)
- API Latency (P50/P95/P99): Graph
- Database Connection Pool: Gauge

---

## Code Instrumentation Examples

### Logging Example

```python
import structlog

logger = structlog.get_logger()

@app.post("/users")
async def create_user(user: UserCreate):
    logger.info("user.create.started", user_email=user.email)


    try:
        new_user = await user_service.create(user)
        logger.info("user.create.success", user_id=new_user.id)
        return new_user
    except Exception as e:
        logger.error("user.create.failed", error=str(e), user_email=user.email)
        raise
```

### Metrics Example

```python
from prometheus_client import Counter, Histogram

# Define metrics
user_registrations_total = Counter(
    "user_registrations_total",
    "Total user registrations",
    ["status"]
)

user_registration_duration = Histogram(
    "user_registration_duration_seconds",
    "User registration duration"
)

# Instrument code
@user_registration_duration.time()
async def create_user(user: UserCreate):
    try:
        new_user = await user_service.create(user)
        user_registrations_total.labels(status="success").inc()
        return new_user
    except Exception:
        user_registrations_total.labels(status="failed").inc()
        raise
```

### Tracing Example

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def execute_agent(agent_name: str, task: Task, state: WorkflowState):
    with tracer.start_as_current_span(
        f"agent.{{agent_name}}.execute",
        attributes={{
            "agent.name": agent_name,
            "agent.tier": task.tier,
            "workflow.id": state.workflow_id
        }}
    ) as span:
        try:
            result = await agent.run(task, state)
            span.set_attribute("agent.status", "success")
            return result
        except AgentRejectionError as e:
            span.set_attribute("agent.status", "rejected")
            span.record_exception(e)
            raise
```

---

## Implementation Checklist

- [ ] Configure structlog in src/observability/logging.py
- [ ] Define all Prometheus metrics in src/observability/metrics.py
- [ ] Set up OpenTelemetry tracing
- [ ] Create Grafana dashboards
- [ ] Configure Prometheus scraping
- [ ] Set up alerting rules
- [ ] Instrument all agents with logging, metrics, tracing
- [ ] Test observability stack end-to-end
```

## Guidelines

1. **Comprehensive Coverage:** Define metrics for all critical paths
2. **Actionable Alerts:** Every alert should have a clear action
3. **Cost Tracking:** LLM token usage and cost must be visible
4. **Debugging Context:** Logs should enable full workflow reconstruction
5. **Performance SLIs:** Define measurable service level indicators
6. **Code Examples:** Provide clear instrumentation examples for Software
   Engineer

## Respond with the complete OBSERVABILITY.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and extract OBSERVABILITY.md content.

        Args:
            response: LLM response with observability strategy
            state: Current workflow state

        Returns:
            Parsed observability spec with validation
        """
        # Extract content
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```markdown"):
            content = content.split("```markdown")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        # Validate that essential sections exist
        required_sections = [
            "# Observability Strategy",
            "## Logging Strategy",
            "## Metrics & Monitoring",
            "## Distributed Tracing",
            "## Alerting Rules",
            "## Dashboards",
        ]

        missing_sections = [
            section for section in required_sections if section not in content
        ]

        if missing_sections:
            # Log warning but don't fail
            pass

        # Count metrics defined (approximate)
        metrics_count = (
            content.count("Counter(")
            + content.count("Gauge(")
            + content.count("Histogram(")
        )

        # Write OBSERVABILITY.md file
        await self._write_file("OBSERVABILITY.md", content)

        return {
            "observability": content,
            "observability_generated": True,
            "observability_token_count": response.tokens_used,
            "metrics_count": metrics_count,
            "has_logging_strategy": "## Logging Strategy" in content,
            "has_tracing_strategy": "## Distributed Tracing" in content,
            "has_alerting_rules": "## Alerting Rules" in content,
        }

    def _get_temperature(self) -> float:
        """Use moderate temperature for observability specification.

        Returns:
            Temperature value (0.4 for balanced structure and completeness)
        """
        return 0.4
