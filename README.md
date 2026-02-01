# Multi-Tier Agent Ecosystem

A production-ready multi-agent orchestration system built with LangGraph, FastAPI, and PostgreSQL. Designed for complex AI workflows with human approval gates, state persistence, and comprehensive observability.

## 🎯 Features

- **Multi-Tier Agent Architecture:** 6-tier hierarchical agent system (Tier 0-5)
- **Workflow Orchestration:** LangGraph-based state management with checkpointing
- **Human Approval Gates:** Pause workflows for human review at critical stages
- **State Persistence:** PostgreSQL-backed checkpoint storage for recovery
- **Observability:** Structured logging, Prometheus metrics, Grafana dashboards
- **API-First Design:** FastAPI REST API with JWT authentication
- **Conversational UI:** Chainlit-based web interface
- **Production Ready:** Docker Compose, health checks, rate limiting
- **CI/CD Integration:** GitHub Actions workflows for testing and security scanning

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### 5-Minute Setup

```bash
# Clone repository
git clone <repository-url>
cd my-agent-team

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Initialize database
docker-compose exec agent-api bash scripts/init_db.sh

# Run migrations
docker-compose exec agent-api bash scripts/run_migrations.sh

# Verify health
docker-compose exec agent-api bash scripts/health_check.sh
```

### Access the Application

- **FastAPI:** http://localhost:8000
- **Chainlit UI:** http://localhost:8080
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)
- **MinIO Console:** http://localhost:9001 (minioadmin/minioadmin123)

## 📋 Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Chainlit Web UI                          │
│              (Conversational Interface)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   FastAPI Backend                           │
│         (REST API, Health Checks, Metrics)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              LangGraph Orchestration                         │
│    (Multi-Agent Workflow, State Management)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼────┐
│PostgreSQL│  │  Redis  │  │  MinIO   │
│(State)   │  │(Cache)  │  │(Artifacts)
└──────────┘  └─────────┘  └──────────┘
```

### Agent Tiers

| Tier | Role | Responsibility |
|------|------|-----------------|
| **Tier 0** | Deviation Handler | Escalation and error recovery |
| **Tier 1** | Strategy & Architecture | Requirements analysis and design |
| **Tier 2** | Planning & Infrastructure | Implementation planning and setup |
| **Tier 3** | Development | Code implementation and testing |
| **Tier 4** | Validation | Security and product validation |
| **Tier 5** | Deployment | Documentation and deployment |

## 📚 Documentation

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Setup, running, testing, and debugging
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - Complete API documentation
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and constraints

## 🛠️ Development

### Local Development

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start databases
docker-compose up -d postgres redis minio

# Initialize database
bash scripts/init_db.sh
bash scripts/run_migrations.sh

# Run FastAPI
uvicorn src.main:app --reload

# In another terminal, run Chainlit
chainlit run src/chainlit_app/app.py -w
```

### Testing

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

## 🐳 Docker

### Build Images

```bash
# Build development image
docker build -f Dockerfile --target development -t agent-ecosystem:dev .

# Build production image
docker build -f Dockerfile --target production -t agent-ecosystem:prod .

# Build Chainlit image
docker build -f Dockerfile.chainlit --target development -t agent-ui:dev .
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset database
docker-compose down -v
docker-compose up -d
```

## 📊 Monitoring

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Run comprehensive health check
bash scripts/health_check.sh
```

### Metrics

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000
- **Metrics Endpoint:** http://localhost:8000/metrics

### Logs

```bash
# View application logs
docker-compose logs agent-api

# View database logs
docker-compose logs postgres

# View all logs
docker-compose logs -f
```

## 🔐 Security

### Authentication

- JWT-based authentication for API endpoints
- Role-based access control (RBAC)
- Secure password hashing with bcrypt

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
- Enable HTTPS in production
- Regularly update dependencies
- Run security scans: `pip-audit`, `safety`

## 🚢 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use strong JWT secret key
- [ ] Enable HTTPS/TLS
- [ ] Configure proper database backups
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Run security scans
- [ ] Load test the application
- [ ] Set up CI/CD pipeline

### Kubernetes Deployment

```bash
# Build production image
docker build -f Dockerfile --target production -t agent-ecosystem:latest .

# Push to registry
docker tag agent-ecosystem:latest your-registry/agent-ecosystem:latest
docker push your-registry/agent-ecosystem:latest

# Deploy with Helm (if available)
helm install agent-ecosystem ./helm-charts
```

## 📈 Performance

### Optimization Tips

- Use connection pooling for database
- Enable Redis caching for frequently accessed data
- Configure appropriate worker count
- Monitor and optimize slow queries
- Use CDN for static assets
- Implement rate limiting

### Benchmarks

- API Response Time: P95 < 500ms
- Database Query Time: < 100ms (with indexes)
- Workflow Execution: Depends on agent complexity
- Memory Usage: ~512MB per worker

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Submit a pull request

### Code Standards

- Follow PEP 8 style guide
- Use type hints for all public functions
- Write docstrings for all modules and functions
- Maintain test coverage > 80%
- Run linting and type checks before committing

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation:** See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Troubleshooting:** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **API Reference:** See [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **Issues:** Open an issue on GitHub
- **Discussions:** Use GitHub Discussions

## 🗺️ Roadmap

### Phase 1-11: Core Implementation ✅
- Multi-tier agent architecture
- Workflow orchestration
- State persistence
- API and UI

### Phase 12: Infrastructure & Deployment 🚀
- Docker and Kubernetes support
- CI/CD pipelines
- Production readiness
- Comprehensive documentation

### Future Enhancements
- Advanced monitoring and alerting
- Multi-region deployment
- Advanced caching strategies
- Performance optimization
- Enterprise features

## 📞 Contact

For questions or support, please contact the development team or open an issue on GitHub.

---

**Last Updated:** 2026-01-30  
**Version:** 1.0.0  
**Status:** Production Ready
