# Aionix Agent Backend

Production-ready FastAPI backend for the Autonomous AI Knowledge Worker system.

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated folders for API routes, business logic, data models, and utilities
- **Authentication**: JWT-based authentication with role-based access control
- **Data Ingestion**: Multiple data sources including NewsAPI, Alpha Vantage, and file uploads
- **Database**: PostgreSQL with SQLAlchemy ORM and async support
- **Security**: Secure file uploads, input validation, and environment-based configuration
- **Monitoring**: Health checks, structured logging, and error handling
- **Documentation**: Auto-generated API documentation with examples

## Architecture

```
backend/
├── api/                    # API routes and dependencies
│   ├── routers/           # FastAPI routers
│   └── dependencies/      # Dependency injection
├── core/                  # Core functionality
│   ├── config/           # Configuration management
│   └── security/         # Security utilities
├── services/             # Business logic services
│   ├── news/            # NewsAPI integration
│   ├── financial/       # Alpha Vantage integration
│   └── upload/          # File upload processing
├── models/               # SQLAlchemy database models
├── schemas/              # Pydantic schemas
├── db/                   # Database connection and session management
├── utils/                # Helper utilities
├── tests/                # Test suites
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── alembic/              # Database migrations
└── app/                  # FastAPI application
```

## Installation

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   # Create PostgreSQL database
   # Run migrations
   alembic upgrade head
   ```

## Configuration

The application uses environment variables for configuration. Copy `env.example` to `.env` and update the values:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/aionix_agent

# API Keys
OPENAI_API_KEY=your_openai_key
NEWS_API_KEY=your_news_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Security
SECRET_KEY=your-secret-key-here
VECTOR_DB_API_KEY=your-vector-db-key

# Environment
ENVIRONMENT=development
```

## Running the Application

### Development
```bash
# From project root (recommended)
python run-backend.py

# Or from backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=aionix_agent --cov-report=html
```

## Key Endpoints

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /upload/files` - Upload documents
- `GET /news/fetch` - Fetch news articles
- `GET /financial/stocks/{symbol}` - Get stock data
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

## Security Best Practices

- All secrets are loaded from environment variables
- Passwords are hashed using bcrypt
- JWT tokens with configurable expiration
- File upload validation and size limits
- CORS configured for specific origins
- Rate limiting on external API calls

## Development

### Code Quality
```bash
# Format code
black .

# Sort imports
isort .

# Type checking
mypy .

# Linting
flake8 .
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "migration message"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## License

MIT License
