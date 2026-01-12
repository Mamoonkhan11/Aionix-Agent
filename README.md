# Aionix Agent - Autonomous AI Knowledge Worker

A comprehensive, production-ready autonomous AI system designed for knowledge workers, featuring advanced task scheduling, multi-agent collaboration, voice interaction, and enterprise-grade security.

## 🏗️ System Architecture

### Core Components

- **Autonomous Task Scheduler**: Celery-based scheduling system with Redis backend
- **Web Search Agent**: SerpAPI-powered autonomous information gathering
- **Pluggable AI Agent Framework**: Modular agent system with specialized agents
- **Multi-User Collaboration**: RBAC-based shared resources and real-time sessions
- **Voice Interface**: Speech-to-text with intent recognition
- **Enterprise Security**: Comprehensive security controls and audit trails

### Technology Stack

**Backend:**
- FastAPI (Python async web framework)
- SQLAlchemy with PostgreSQL (async ORM)
- Celery + Redis (task queue)
- Pydantic (data validation)
- OpenAI/LangChain (AI integration)

**Frontend:**
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- Real-time WebSocket support

**Infrastructure:**
- Docker containerization
- Environment-based configuration
- Structured logging with JSON
- Health checks and monitoring

## 🚀 Key Features

### 1. Autonomous Task Scheduler
- **Daily/Weekly Scheduling**: Configurable recurring tasks
- **Persistent Definitions**: Database-backed task storage
- **Graceful Failure Recovery**: Automatic retry mechanisms
- **Execution Logging**: Comprehensive task execution tracking

### 2. Web Search Agent
- **Autonomous Searching**: Periodic web information gathering
- **Duplicate Prevention**: Content hashing and deduplication
- **API Integration**: SerpAPI with rate limiting
- **Pipeline Integration**: Automatic AI processing feed

### 3. Pluggable Agent Framework
- **Base Agent Class**: Extensible agent architecture
- **Specialized Agents**:
  - Finance Agent (market analysis, investment advice)
  - News Agent (sentiment analysis, trend identification)
  - Research Agent (comprehensive analysis, synthesis)
- **Dynamic Registration**: Runtime agent loading
- **Capability-Based Selection**: Automatic agent routing

### 4. Multi-User Collaboration
- **Shared Resources**: Tasks, reports, and agent outputs
- **Access Control**: Granular RBAC permissions
- **Real-Time Sessions**: Collaborative workspaces
- **Activity Logging**: Comprehensive audit trails

### 5. Voice Interface
- **Speech-to-Text**: Multiple language support
- **Intent Recognition**: Natural language understanding
- **Command Processing**: Voice-activated AI tasks
- **Audio Streaming**: Real-time voice processing

## 📁 Project Structure

```
Aionix Agent/
├── backend/
│   ├── ai_engine/
│   │   ├── agents/          # Pluggable agent framework
│   │   ├── chains/          # LangChain processing chains
│   │   ├── embeddings/      # Vector embeddings service
│   │   ├── llm_client.py    # LLM integration
│   │   ├── memory/          # Conversation memory
│   │   └── orchestration/   # Task orchestration
│   ├── api/
│   │   ├── routers/         # API endpoint routers
│   │   └── dependencies/    # FastAPI dependencies
│   ├── core/
│   │   ├── config/          # Configuration management
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── logging_config.py # Logging setup
│   │   └── security/        # Security utilities
│   ├── models/              # SQLAlchemy models
│   ├── services/            # Business logic services
│   └── tests/               # Test suites
├── frontend/
│   ├── app/                 # Next.js app router
│   ├── components/          # React components
│   ├── context/             # React context providers
│   └── lib/                 # Utility functions
└── docker/                  # Docker configurations
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 13+
- Redis 6+
- Docker & Docker Compose (optional)

### Backend Setup

1. **Clone and navigate:**
   ```bash
   git clone <repository-url>
   cd aionix-agent/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database setup:**
   ```bash
   # Initialize database
   python -c "from db.database import init_database; import asyncio; asyncio.run(init_database())"
   ```

5. **Create admin user:**
   ```bash
   python scripts/create_admin_user.py
   ```

6. **Start services:**
   ```bash
   # Start Redis (if not using Docker)
   redis-server

   # Start Celery worker (in separate terminal)
   celery -A services.scheduler.celery_app worker --loglevel=info

   # Start FastAPI server
   python ../run-backend.py
   ```

### Quick Setup (Windows)

Run the automated setup script:
```bash
setup.bat
```

### Frontend Setup

1. **Navigate to frontend:**
   ```bash
   cd ../frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Environment configuration:**
   ```bash
   cp .env.example .env.local
   # Configure API endpoints
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Or for production
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 API Documentation

### Core Endpoints

#### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Token refresh

#### Task Scheduler
- `POST /scheduler/tasks` - Create scheduled task
- `GET /scheduler/tasks` - List user tasks
- `PUT /scheduler/tasks/{id}` - Update task
- `POST /scheduler/tasks/{id}/execute` - Execute task now

#### Web Search
- `POST /web-search/search` - Perform web search
- `GET /web-search/suggestions` - Get search suggestions

#### Agent Framework
- `GET /agents/` - List available agents
- `POST /agents/{name}/execute` - Execute specific agent
- `POST /agents/chain/execute` - Execute agent chain

#### Collaboration
- `POST /collaboration/share` - Share resource
- `GET /collaboration/shared` - Get shared resources
- `POST /collaboration/sessions` - Create session
- `POST /collaboration/comments` - Add comment

#### Voice Interface
- `POST /voice/process/audio` - Process audio file
- `POST /voice/process/base64` - Process base64 audio
- `GET /voice/status` - Voice service status

### OpenAPI Specification

Access the interactive API documentation at:
- **Development**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/aionix_agent

# AI Services
OPENAI_API_KEY=your_openai_key
SERPAPI_API_KEY=your_serpapi_key

# Task Scheduling
REDIS_URL=redis://localhost:6379/0
ENABLE_CELERY=true

# Security
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs
NEWS_API_KEY=your_news_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

### Agent Configuration

Agents are configured via the `AgentConfig` class:

```python
from ai_engine.agents.base_agent import AgentConfig

config = AgentConfig(
    name="finance_agent",
    description="Financial analysis specialist",
    capabilities=["stock_analysis", "market_trends"],
    parameters={"risk_tolerance": "moderate"},
    memory_enabled=True,
    max_iterations=10
)
```

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Frontend Tests

```bash
# Run unit tests
npm test

# Run E2E tests
npm run test:e2e
```

### Load Testing

```bash
# API load testing
locust -f tests/load/locustfile.py

# Task scheduler stress testing
python tests/load/scheduler_load_test.py
```

## 🚀 Deployment

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] Redis cluster configured
- [ ] Monitoring and logging set up
- [ ] Backup strategy implemented
- [ ] Security hardening applied

### Docker Production

```bash
# Build production images
docker build -f docker/Dockerfile.backend -t aionix-backend:latest .
docker build -f docker/Dockerfile.frontend -t aionix-frontend:latest .

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale celery-worker=3
```

### Cloud Deployment

#### Vercel (Frontend)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

#### Railway/Render (Backend)
- Connect GitHub repository
- Configure environment variables
- Set up PostgreSQL and Redis add-ons
- Deploy with provided Dockerfiles

## 🔒 Security Features

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- Multi-factor authentication support
- Session management

### Data Protection
- Input sanitization and validation
- SQL injection prevention
- XSS protection
- CSRF protection

### API Security
- Rate limiting per user/IP
- Request/response encryption
- API key management
- Audit logging

### Compliance
- GDPR-ready data handling
- Data retention policies
- Privacy-by-design principles
- Regular security audits

## 📊 Monitoring & Observability

### Metrics
- Application performance metrics
- Task execution statistics
- API response times
- Error rates and patterns

### Logging
- Structured JSON logging
- Log aggregation and analysis
- Real-time log streaming
- Historical log retention

### Health Checks
- Application health endpoints
- Database connectivity checks
- External service availability
- Resource utilization monitoring

## 🔄 Backup & Recovery

### Database Backups
```bash
# Automated daily backups
pg_dump aionix_agent > backup_$(date +%Y%m%d).sql

# Restore from backup
psql aionix_agent < backup_20241201.sql
```

### Configuration Backup
- Environment variables versioning
- Configuration drift detection
- Automated rollback procedures

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- **Code Style**: Black formatting, isort imports
- **Testing**: 80%+ code coverage required
- **Documentation**: Update docs for API changes
- **Security**: Run security scans before PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Reference](docs/api/)
- [User Guide](docs/user-guide/)
- [Developer Guide](docs/developer/)

### Community
- [GitHub Issues](https://github.com/your-org/aionix-agent/issues)
- [Discussions](https://github.com/your-org/aionix-agent/discussions)
- [Discord Community](https://discord.gg/aionix)

### Enterprise Support
- Email: enterprise@aionix.ai
- Phone: +1 (555) 123-4567
- Portal: https://support.aionix.ai

## 🗺️ Roadmap

### Phase 1 (Current) ✅
- Core autonomous task scheduling
- Web search agent with SerpAPI
- Pluggable agent framework
- Multi-user collaboration
- Voice interface

### Phase 2 (Next)
- [ ] Offline mode with caching
- [ ] Advanced AI model integration
- [ ] Real-time collaborative editing
- [ ] Mobile app companion
- [ ] Advanced analytics dashboard

### Phase 3 (Future)
- [ ] Multi-tenant architecture
- [ ] Advanced ML model training
- [ ] Integration marketplace
- [ ] Voice conversation flows
- [ ] Predictive task scheduling

---

**Built with ❤️ by the Aionix Team**

*Empowering knowledge workers with autonomous AI capabilities*