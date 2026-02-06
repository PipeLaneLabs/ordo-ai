# Multi-Tier Agent Ecosystem

> [!WARNING]  
> **Current Status: Early Alpha / Development Phase**  
> This project is currently under active development. The core architecture is implemented, but the system is not yet fully functional or tested. **It is not suitable for production use at this time.**

A multi-agent orchestration system built with LangGraph, FastAPI, and PostgreSQL. This project explores complex AI workflows featuring a 6-tier hierarchical structure, human-in-the-loop approval gates, and integrated observability.

---

## 🧪 Project Health & Testing

| Component | Status | Notes |
|-----------|--------|-------|
| Agent Orchestration | 🚧 WIP | LangGraph logic implemented; validation pending |
| API Backend | ✅ Functional | FastAPI endpoints structured; auth needs testing |
| Database/State | ✅ Functional | Postgres schema ready; migration scripts need verification |
| Observability | ✅ Functional | Prometheus/Grafana stacks are containerized |
| Human-in-the-loop | 🚧 WIP | Approval gates under development |

---

## 🎯 Features (Under Construction)

- **Multi-Tier Agent Architecture:** 6-tier hierarchical system (Tier 0-5) for specialized task delegation
- **State Management:** LangGraph-based persistence with PostgreSQL checkpointing for long-running workflows
- **Human-in-the-loop:** Planned approval gates to pause workflows for manual review
- **Observability Stack:** Pre-configured Prometheus and Grafana dashboards for agent performance metrics
- **Containerized Architecture:** Docker Compose setup for local development and database orchestration
- **API-First Design:** FastAPI REST API with JWT authentication
- **Conversational UI:** Chainlit-based web interface (experimental)

---

## 📋 Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Chainlit Web UI                           │
│              (Conversational Interface)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   FastAPI Backend                           │
│         (REST API, Health Checks, Metrics)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                LangGraph Orchestration                      │
│    (Multi-Agent Workflow, State Management)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼────┐
│PostgreSQL│  │  Redis  │  │  MinIO   │
│(State)   │  │(Cache)  │  │(Artifacts)│
└──────────┘  └─────────┘  └──────────┘
```

### Agent Tiers

| Tier | Role | Responsibility |
|------|------|----------------|
| **Tier 0** | Deviation Handler | Escalation and error recovery |
| **Tier 1** | Strategy & Architecture | Requirements analysis and design |
| **Tier 2** | Planning & Infrastructure | Implementation planning and setup |
| **Tier 3** | Development | Code implementation and testing |
| **Tier 4** | Validation | Security and product validation |
| **Tier 5** | Deployment | Documentation and deployment |

---

## 🛠️ Development Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### Local Installation

```bash
# Clone repository
git clone <repository-url>
cd my-agent-team

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
```

### Starting the Stack

The infrastructure can be launched via Docker, though application logic is currently being stabilized:

```bash
# Start databases and monitoring
docker-compose up -d postgres redis minio prometheus grafana

# Initialize database (Experimental)
bash scripts/init_db.sh
bash scripts/run_migrations.sh

# Verify health (may fail in current state)
bash scripts/health_check.sh
```

### Access Points (When Running)

- **FastAPI:** http://localhost:8000
- **Chainlit UI:** http://localhost:8080
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)
- **MinIO Console:** http://localhost:9001 (minioadmin/minioadmin123)

---

## 🧪 Testing (In Development)

### Current Testing Status

- **Unit Tests:** 🚧 In Progress
- **Integration Tests:** ❌ Pending
- **E2E Workflows:** ❌ Pending

> [!NOTE]  
> The core orchestration logic is implemented, but edge cases and state recovery have not been fully validated. Use with caution.

### Running Tests (When Available)

```bash
# Run all tests
pytest tests/ -v --cov=src

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/ --ignore-missing-imports

# All checks
black --check src/ tests/ && ruff check src/ tests/ && mypy src/
```

---

## 📚 Documentation

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Setup, running, testing, and debugging
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - Complete API documentation
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and constraints

---

## 📈 Roadmap to v1.0.0

### Phase 1: Core Stabilization (Current)
- [ ] Finalize LangGraph state transitions and edge cases
- [ ] Implement comprehensive Unit Testing suite (Pytest)
- [ ] Validate PostgreSQL checkpointing and recovery
- [ ] Fix known bugs in agent orchestration

### Phase 2: Integration & Validation
- [ ] End-to-End (E2E) workflow testing
- [ ] Integration tests for all components
- [ ] Human-in-the-loop approval gate implementation
- [ ] Security audit and vulnerability scanning

### Phase 3: Production Hardening
- [ ] Performance optimization and benchmarking
- [ ] Rate limiting and resource management
- [ ] Comprehensive error handling and recovery
- [ ] Load testing and scalability validation

### Phase 4: Documentation & Release
- [ ] Complete API documentation
- [ ] Deployment guides and best practices
- [ ] Example workflows and tutorials
- [ ] v1.0.0 Release

---

## 🤝 Contributing

We welcome contributions, especially in the following areas:

- **Testing:** Writing unit and integration tests for the FastAPI backend and LangGraph workflows
- **Bug Reports:** Identifying failures in the current alpha build
- **Documentation:** Refining the LangGraph orchestration flow documentation
- **Feature Development:** Implementing human-in-the-loop approval gates

### How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and commit: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guide
- Use type hints for all public functions
- Write docstrings for all modules and functions
- Maintain test coverage > 80% (target for v1.0.0)
- Run linting and type checks before committing

---

## 🔐 Security

### Environment Variables

All sensitive configuration is managed via environment variables:

```bash
# Copy and configure
cp .env.example .env

# Required variables
OPENROUTER_API_KEY=your-key
GOOGLE_API_KEY=your-key
JWT_SECRET_KEY=your-secret-key-min-32-chars
```

### Security Best Practices

- Never commit `.env` file to version control
- Use strong JWT secret keys (32+ characters)
- Regularly update dependencies
- Run security scans: `pip-audit`, `safety`

---

## 🛠️ Future Deployment Considerations

Once the project reaches stability, deployment will follow these patterns:

### Production Checklist (v1.0.0+)

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use strong JWT secret key
- [ ] Enable HTTPS/TLS
- [ ] Configure proper database backups
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Run security scans
- [ ] Load test the application
- [ ] Set up CI/CD pipeline

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Support

- **Documentation:** See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Troubleshooting:** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **API Reference:** See [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **Issues:** Open an issue on GitHub
- **Discussions:** Use GitHub Discussions

---

## 📞 Contact

For questions or support, please contact the development team or open an issue on GitHub.

---

**Last Updated:** 2026-02-06  
**Version:** 0.1.0-alpha  
**Status:** Under Active Development / Untested
