# Competitive Intelligence System - Project Structure

## 📁 Directory Organization

```
competitive-intelligence/
├── src/                              # Source code
│   ├── __init__.py                   # Package initialization
│   ├── app_postgres.py               # Main Flask application
│   ├── config.py                     # Configuration management
│   ├── orchestrator.py               # Main orchestration logic
│   ├── models/                       # Data models
│   │   ├── __init__.py
│   │   └── database.py               # SQLAlchemy models
│   ├── services/                     # Business logic services
│   │   ├── __init__.py
│   │   ├── ai_summarization.py       # AI summarization service
│   │   ├── alerting_service.py       # Slack/email alerting
│   │   ├── analyzer.py               # Content analysis
│   │   └── scraper.py                # Web scraping service
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── formatter.py              # Data formatting utilities
│       ├── monitoring.py             # Basic monitoring dashboard
│       └── production_monitoring.py  # Production monitoring
├── sql/                              # Database scripts
│   ├── schema.sql                    # PostgreSQL schema
│   ├── example_queries.sql           # Example SQL queries
│   └── setup_postgres.py             # Database initialization
├── deployment/                       # Deployment configurations
│   ├── docker/                       # Docker configurations
│   │   ├── Dockerfile                # Application container
│   │   └── docker-compose.yml        # Multi-service setup
│   ├── nginx/                        # Reverse proxy configuration
│   │   └── nginx.conf                # Nginx configuration
│   └── scripts/                      # Deployment scripts
│       ├── init_production_db.sh     # Production DB setup
│       └── setup_local.sh            # Local development setup
├── docs/                             # Documentation
│   ├── PRODUCTION_DEPLOYMENT.md      # Production deployment guide
│   ├── cloud_deployment_guide.md     # Cloud deployment strategies
│   └── PROJECT_STRUCTURE.md          # This file
├── tests/                            # Test suites
│   ├── test_scraper.py              # Scraper tests
│   ├── test_*.py                    # Other test files
│   └── __init__.py
├── templates/                        # HTML templates
│   └── index.html                   # Dashboard template
├── assets/                           # Static assets
│   └── logo.png                     # Application logo
├── logs/                             # Application logs
├── reports/                          # Generated reports
├── summaries/                        # Content summaries
├── instance/                         # Instance-specific files
│   └── market_intelligence.db       # SQLite database (if used)
├── .env.example                     # Environment template
├── .env.production.example          # Production environment template
├── requirements.txt                 # Python dependencies
├── README.md                        # Project documentation
└── watchlist.json                   # Competitor watchlist
```

## 🏗️ Architecture Overview

### Core Components

1. **Flask Web Application** (`src/app_postgres.py`)
   - Human-in-the-loop triage dashboard
   - REST API endpoints
   - Health monitoring endpoints

2. **Services Layer** (`src/services/`)
   - **AI Summarization**: OpenAI GPT-4 integration for content analysis
   - **Alerting Service**: Slack/email notifications for high-priority updates
   - **Web Scraper**: Multi-source content extraction
   - **Content Analyzer**: Quality scoring and categorization

3. **Database Layer** (`sql/`)
   - PostgreSQL schema with audit trails
   - Full-text search capabilities
   - Deduplication and quality controls

4. **Deployment Infrastructure** (`deployment/`)
   - Docker containerization
   - Nginx reverse proxy
   - Production deployment scripts

## 🔄 Data Flow

```
1. Web Scraper → Raw Content Queue (raw_fetch_queue)
2. AI Summarization → Content Analysis & Scoring
3. Human Triage → Approval/Rejection
4. Approved Content → Competitor Updates (competitor_updates)
5. High Priority Updates → Alerting Service
6. Alerts → Slack/Email Notifications
```

## 🛠️ Development Workflow

### Local Development
```bash
# Set up environment
cd deployment/scripts
chmod +x setup_local.sh
./setup_local.sh

# Activate virtual environment
source venv/bin/activate

# Run development server
python src/app_postgres.py
```

### Production Deployment
```bash
# Docker deployment
cd deployment/docker
docker-compose up -d

# Health check
curl http://localhost/health
```

## 📊 Monitoring & Observability

- **Health Endpoints**: `/health`, `/health/detailed`
- **Metrics**: `/metrics` (Prometheus format)
- **Structured Logging**: JSON format with log rotation
- **Database Monitoring**: Connection pooling, slow query detection
- **Performance Tracking**: Request timing, error rates

## 🔐 Security Features

- Environment variable configuration
- SQL injection prevention (SQLAlchemy ORM)
- Rate limiting (Nginx)
- HTTPS support
- Security headers
- Audit trail logging

## 🔧 Configuration Management

- **Development**: `.env` file
- **Production**: Environment variables + `.env.production.example`
- **Docker**: `docker-compose.yml` environment section

## 📈 Scalability Considerations

- **Horizontal Scaling**: Load balancer ready
- **Database**: PostgreSQL with read replicas
- **Caching**: Redis integration ready
- **Queue System**: Background job processing
- **Container Orchestration**: Kubernetes ready

## 🧪 Testing Strategy

- Unit tests in `tests/` directory
- Integration tests for services
- End-to-end API testing
- Database migration testing

## 📚 Documentation

- **Production Guide**: `docs/PRODUCTION_DEPLOYMENT.md`
- **Cloud Deployment**: `docs/cloud_deployment_guide.md`
- **API Documentation**: Available at `/docs` endpoint
- **Database Schema**: Documented in `sql/schema.sql`

---

This structure provides clear separation of concerns, making the codebase maintainable and scalable for enterprise deployment.
