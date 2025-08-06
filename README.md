![Market Intelligence Logo](assets/logo.png)

# Competitive Intelligence System

A production-ready competitive intelligence platform with AI-powered analysis, human-in-the-loop triage, and automated alerting.

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)
```bash
# Clone and navigate
git clone <repository-url>
cd Market-Intelligence-Repository

# Start with Docker
chmod +x launch.sh
./launch.sh docker
```

### Option 2: Local Development
```bash
# Set up local environment
./launch.sh local

# Or manually:
chmod +x deployment/scripts/setup_local.sh
./deployment/scripts/setup_local.sh
source venv/bin/activate
python src/app_postgres.py
```

## 📁 Project Structure

```
competitive-intelligence/
├── src/                              # Source code
│   ├── app_postgres.py               # Main Flask application
│   ├── services/                     # Business logic
│   │   ├── ai_summarization.py       # AI-powered content analysis
│   │   ├── alerting_service.py       # Slack/email notifications
│   │   └── scraper.py                # Web scraping service
│   └── utils/                        # Utilities and monitoring
├── sql/                              # Database schema and scripts
├── deployment/                       # Docker and deployment configs
├── docs/                             # Documentation
├── tests/                            # Test suite
└── templates/                        # Web UI templates
```

## 🔧 Configuration

1. **Environment Setup**
```bash
cp .env.production.example .env
# Edit .env with your configuration
```

2. **Required Variables**
```bash
# Database
DB_HOST=localhost
DB_NAME=competitive_intelligence
DB_USER=postgres
DB_PASSWORD=your_password

# AI Service
OPENAI_API_KEY=your_openai_key

# Alerting
SLACK_WEBHOOK_URL=your_slack_webhook
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=your_email
EMAIL_PASSWORD=your_app_password
```
# AI Service
OPENAI_API_KEY=your_openai_key

# Alerting
SLACK_WEBHOOK_URL=your_slack_webhook
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=your_email
EMAIL_PASSWORD=your_app_password
```

## 🎯 Features

### Core Capabilities
- **Multi-Source Scraping**: Automated content collection from competitor websites
- **AI-Powered Analysis**: GPT-4 integration for intelligent content summarization
- **Human-in-the-Loop Triage**: Web dashboard for content approval workflow
- **Smart Alerting**: Slack and email notifications for high-priority updates
- **Full Audit Trail**: Complete tracking of all content and approval decisions

### Technical Features
- **Production-Ready**: Docker containerization with health checks
- **Scalable Architecture**: PostgreSQL with full-text search and indexing
- **Comprehensive Monitoring**: Structured logging, metrics, and health endpoints
- **Security First**: Rate limiting, input validation, and audit logging
- **Cloud-Ready**: AWS/GCP/Azure deployment guides included

## 📊 Monitoring & Health

- **Health Check**: `GET /health`
- **Detailed Status**: `GET /health/detailed`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Dashboard**: Available at root URL

## 🔒 Security

- Environment-based configuration
- SQL injection prevention
- Rate limiting and security headers
- Audit trail for all actions
- HTTPS support in production

## 📚 Documentation

- [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)
- [Cloud Deployment Strategies](docs/cloud_deployment_guide.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)

## 🛠️ Development

### Running Tests
```bash
source venv/bin/activate
python -m pytest tests/
```

### Database Operations
```bash
# Initialize database
python sql/setup_postgres.py

# Run migrations (if any)
python src/app_postgres.py db upgrade
```

### Monitoring
```bash
# View application logs
tail -f logs/app.log

# Monitor with dashboard
python src/utils/monitoring.py
```

## 🧹 Cleanup

```bash
# Basic cleanup
./cleanup.sh

# Complete cleanup (removes Docker, venv, databases)
./cleanup.sh all
```

## 🤝 Contributing

1. Follow the established directory structure
2. Add tests for new features
3. Update documentation
4. Ensure all health checks pass
5. Test both local and Docker deployments

## 📈 Scaling

The system is designed for enterprise scale:
- Horizontal scaling with load balancers
- Database read replicas
- Redis caching layer
- Background job processing
- Container orchestration ready

## 📄 License

[Your License Here]

---

For detailed deployment instructions, see [PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md).
- Maximum articles per company
- Output directory

## Requirements

- Python 3.7+
- See `requirements.txt` for package dependencies 