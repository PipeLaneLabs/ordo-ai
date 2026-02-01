"""Solution Architect Agent for Tier 1.

Designs system architecture including:
- Technology stack selection
- System design and architecture
- Architectural Decision Records (ADRs)
- Security architecture
- Coding standards and conventions
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class SolutionArchitectAgent(BaseAgent):
    """Tier 1 agent for system architecture and design.

    Uses DeepSeek-R1 for architectural reasoning and design decisions.
    Generates ARCHITECTURE.md with technology stack, ADRs, and standards.

    Attributes:
        token_budget: 8,000 tokens for comprehensive architecture design
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Solution Architect Agent.

        Args:
            llm_client: LLM client (should use DeepSeek-R1 for reasoning)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="SolutionArchitectAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=8000,  # 8K tokens for architecture design
        )

    async def _build_prompt(
        self,
        state: WorkflowState,
        **_kwargs: object,
    ) -> str:
        """Build architecture design prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for architecture design
        """
        requirements = state.get("requirements", "")
        if not requirements:
            requirements = await self._read_if_exists("REQUIREMENTS.md") or ""

        validation_report = state.get("validation_report", "")
        if not validation_report:
            validation_report = await self._read_if_exists("VALIDATION_REPORT.md") or ""

        prompt = f"""# System Architecture Design Task

## Requirements
{requirements}

## Validation Report
{validation_report}

## Your Task

As a Solution Architect, design a comprehensive system architecture for this project.

### Architecture Design Framework

#### 1. **Technology Stack Selection**
Choose appropriate technologies for:
- **Backend:** Programming language, framework, API style (REST/GraphQL)
- **Frontend:** Framework, state management, build tools
- **Database:** Type (SQL/NoSQL), specific database, ORM
- **Caching:** Redis, Memcached, in-memory
- **Message Queue:** RabbitMQ, Kafka, SQS (if needed)
- **Infrastructure:** Cloud provider, containers, orchestration
- **DevOps:** CI/CD, monitoring, logging

**Selection Criteria:**
- Meets performance requirements
- Team expertise
- Community support
- Long-term maintainability
- Cost-effectiveness

#### 2. **System Design**
Create architecture diagrams and descriptions:
- **High-Level Architecture:** System components and interactions
- **Component Diagram:** Internal modules and dependencies
- **Data Flow:** How data moves through the system
- **Deployment Architecture:** Production infrastructure
- **Security Architecture:** Security layers and controls

#### 3. **Architectural Decision Records (ADRs)**
Document key decisions:
- **Format:** ADR-XXX: [Decision Title]
- **Context:** Why this decision was needed
- **Decision:** What was decided
- **Consequences:** Trade-offs and implications
- **Alternatives:** What else was considered

#### 4. **Security Architecture**
Define security layers:
- **Authentication:** Mechanism (JWT, OAuth, etc.)
- **Authorization:** Access control model (RBAC, ABAC)
- **Data Protection:** Encryption at rest and in transit
- **Network Security:** Firewalls, VPC, security groups
- **Application Security:** Input validation, CSRF protection
- **Secrets Management:** How credentials are stored
- **Audit Logging:** Security event tracking

#### 5. **Coding Standards**
Define conventions:
- **Naming Conventions:** Classes, functions, variables
- **Code Organization:** Directory structure, module layout
- **Documentation Standards:** Docstrings, comments, README
- **Error Handling:** Exception patterns, logging
- **Testing Standards:** Coverage requirements, test organization
- **Code Quality:** Linting rules, complexity limits

## Output Format

Generate an ARCHITECTURE.md document:

```markdown
# System Architecture

**Project:** [Project Name]
**Version:** 1.0
**Date:** [Current Date]
**Architect:** Solution Architect Agent

---

## 1. Executive Summary

[Brief overview of the architecture and key design principles]

---

## 2. Technology Stack

### 2.1 Backend
- **Language:** [e.g., Python 3.12]
- **Framework:** [e.g., FastAPI 0.110+]
- **API Style:** [REST/GraphQL/gRPC]
- **Authentication:** [JWT/OAuth 2.0/etc.]

### 2.2 Frontend
- **Framework:** [React/Vue/Angular/etc.]
- **State Management:** [Redux/Zustand/etc.]
- **Styling:** [Tailwind/CSS Modules/etc.]

### 2.3 Database
- **Primary Database:** [PostgreSQL/MySQL/MongoDB/etc.]
- **ORM/ODM:** [SQLAlchemy/Prisma/etc.]
- **Migrations:** [Alembic/Flyway/etc.]
- **Caching:** [Redis/Memcached/etc.]

### 2.4 Infrastructure
- **Cloud Provider:** [AWS/Azure/GCP/On-premise]
- **Containers:** [Docker]
- **Orchestration:** [Kubernetes/ECS/Docker Compose]
- **Load Balancer:** [Application LoadBalancer/NGINX]

### 2.5 DevOps
- **CI/CD:** [GitHub Actions/GitLab CI/Jenkins]
- **Monitoring:** [Prometheus/Grafana/Datadog]
- **Logging:** [ELK Stack/CloudWatch]
- **Version Control:** [Git/GitHub/GitLab]

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
[Diagram or ASCII art representation]
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   API       │────▶│  Database   │
│  (Frontend) │     │  (Backend)  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │   Cache     │
                    │   (Redis)   │
                    └─────────────┘
```

**Description:** [Explain the architecture]

### 3.2 Component Diagram

**Components:**
1. **API Layer:** [Description]
2. **Business Logic Layer:** [Description]
3. **Data Access Layer:** [Description]
4. **External Services:** [Description]

**Dependencies:** [How components interact]

### 3.3 Data Flow

1. [Step 1: Client request]
2. [Step 2: Authentication]
3. [Step 3: Business logic]
4. [Step 4: Data persistence]
5. [Step 5: Response]

### 3.4 Deployment Architecture

**Environments:**
- **Development:** [Configuration]
- **Staging:** [Configuration]
- **Production:** [Configuration + HA/DR]

**Scaling Strategy:** [Horizontal/Vertical, auto-scaling rules]

---

## 4. Architectural Decision Records (ADRs)

### ADR-001: [Decision Title]
- **Status:** Accepted
- **Context:** [Why this decision was needed]
- **Decision:** [What was decided]
- **Consequences:** [Positive and negative outcomes]
- **Alternatives Considered:** [What else was evaluated]

[Continue for all major decisions]

---

## 5. Security Architecture

### 5.1 Authentication
- **Mechanism:** [JWT/OAuth/etc.]
- **Token Storage:** [HttpOnly cookies/localStorage]
- **Token Expiry:** [15 minutes access, 7 days refresh]

### 5.2 Authorization
- **Model:** [RBAC - Role-Based Access Control]
- **Roles:** [Admin, User, Guest, etc.]
- **Permissions:** [Read, Write, Delete, etc.]

### 5.3 Data Protection
- **At Rest:** [AES-256 encryption for sensitive fields]
- **In Transit:** [TLS 1.3, HTTPS only]
- **PII Handling:** [Encryption, access controls]

### 5.4 Application Security
- **Input Validation:** [Pydantic schemas, sanitization]
- **CSRF Protection:** [Double-submit cookies]
- **XSS Protection:** [Content Security Policy]
- **SQL Injection:** [Parameterized queries, ORM]

### 5.5 Secrets Management
- **Development:** [.env files (gitignored)]
- **Production:** [AWS Secrets Manager/Vault]

### 5.6 Audit Logging
- **Events Logged:** [Authentication, authorization, data changes]
- **Retention:** [90 days minimum]
- **Format:** [JSON structured logs]

---

## 6. Coding Standards

### 6.1 Naming Conventions
- **Classes:** PascalCase (e.g., `UserService`)
- **Functions:** snake_case (e.g., `create_user`)
- **Variables:** snake_case (e.g., `user_id`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)

### 6.2 Code Organization
```
project/
├── src/
│   ├── api/          # API routes
│   ├── services/     # Business logic
│   ├── models/       # Data models
│   ├── repositories/ # Database access
│   └── utils/        # Shared utilities
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/
```

### 6.3 Documentation Standards
- **Docstrings:** Google style for Python, JSDoc for JavaScript
- **Comments:** Explain "why", not "what"
- **README:** Setup instructions, architecture overview
- **API Docs:** OpenAPI/Swagger spec

### 6.4 Error Handling
- **Custom Exceptions:** Domain-specific error classes
- **Logging:** Structured logging with context
- **User-Facing Errors:** Clear, actionable messages

### 6.5 Testing Standards
- **Coverage Target:** 70% minimum
- **Test Types:** Unit (60%), Integration (30%), E2E (10%)
- **Test Naming:** `test_<function>_<scenario>_<expected_result>`

### 6.6 Code Quality
- **Linting:** Ruff for Python, ESLint for JavaScript
- **Formatting:** Black for Python, Prettier for JavaScript
- **Complexity:** Max cyclomatic complexity: 10
- **Line Length:** 88 characters for Python, 100 for JavaScript

---

## 7. Non-Functional Requirements Implementation

### 7.1 Performance
- **Response Time:** API calls < 200ms (p95)
- **Throughput:** Handle 1000 requests/second
- **Optimization:** Database indexing, caching, CDN

### 7.2 Scalability
- **Horizontal Scaling:** Stateless application servers
- **Database:** Read replicas, connection pooling
- **Caching:** Redis for session and data caching

### 7.3 Availability
- **Target:** 99.9% uptime (43 minutes downtime/month)
- **High Availability:** Multi-AZ deployment
- **Disaster Recovery:** Daily backups, 4-hour RTO

### 7.4 Monitoring \u0026 Observability
- **Metrics:** Prometheus for system metrics
- **Logs:** Centralized logging (ELK/CloudWatch)
- **Traces:** Distributed tracing (Jaeger/X-Ray)
- **Alerts:** PagerDuty for critical issues

---

## 8. Data Architecture

### 8.1 Database Schema
[High-level description of main entities and relationships]

### 8.2 Data Lifecycle
- **Retention:** [Active data: unlimited, archived data: 7 years]
- **Archival:** [Cold storage for data > 1 year old]
- **Deletion:** [GDPR right to be forgotten compliance]

### 8.3 Data Migration Strategy
- **Tool:** [Alembic for Python, Flyway for Java]
- **Process:** Version-controlled migrations, rollback tested

---

## 9. Integration Points

### 9.1 External APIs
- **Service 1:** [Purpose, authentication, rate limits]
- **Service 2:** [Purpose, authentication, rate limits]

### 9.2 Webhooks
- **Incoming:** [Event sources]
- **Outgoing:** [Event destinations]

### 9.3 Message Queues
- **Purpose:** [Async processing, event-driven architecture]
- **Technology:** [RabbitMQ/Kafka/SQS]

---

## 10. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk 1] | [High/Medium/Low] | [High/Medium/Low] | [Strategy] |

---

## 11. Future Considerations

- **Phase 2 Features:** [Planned enhancements]
- **Scalability Path:** [How to scale beyond initial design]
- **Technology Evolution:** [Areas for future modernization]

---

## 12. Glossary

- **Term 1:** Definition
- **Term 2:** Definition

---

## 13. References

- [Relevant design patterns]
- [Industry best practices]
- [Security standards (OWASP, CWE)]
```

## Design Principles

1. **SOLID Principles:** Single Responsibility, Open/Closed, Liskov Substitution,
   Interface Segregation, Dependency Inversion
2. **DRY:** Don't Repeat Yourself
3. **KISS:** Keep It Simple, Stupid
4. **YAGNI:** You Aren't Gonna Need It
5. **Security by Design:** Security is not bolt-on
6. **Fail Fast:** Validate early, fail early
7. **Separation of Concerns:** Clear boundaries between layers

## Respond with the complete ARCHITECTURE.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse architecture document and extract key components.

        Args:
            response: LLM response with architecture document
            state: Current workflow state

        Returns:
            Architecture details and metadata
        """
        # Extract content
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```markdown"):
            content = content.split("```markdown")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        # Write ARCHITECTURE.md file
        await self._write_file("ARCHITECTURE.md", content)

        # Extract technology stack (simple parsing)
        tech_stack = {}
        if "### 2.1 Backend" in content:
            tech_stack["backend"] = "Defined"
        if "### 2.2 Frontend" in content:
            tech_stack["frontend"] = "Defined"
        if "### 2.3 Database" in content:
            tech_stack["database"] = "Defined"

        # Count ADRs
        adr_count = content.count("### ADR-")

        return {
            "architecture": content,
            "architecture_generated": True,
            "tech_stack": tech_stack,
            "adr_count": adr_count,
            "architecture_token_count": response.tokens_used,
            "architecture_sections": len(
                [line for line in content.split("\n") if line.startswith("##")]
            ),
        }

    def _get_temperature(self) -> float:
        """Use moderate temperature for balanced architecture design.

        Returns:
            Temperature value (0.5 for structured yet creative design)
        """
        return 0.5
