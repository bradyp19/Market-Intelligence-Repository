# Production Deployment Guide - Competitive Intelligence System

## Overview
This guide provides step-by-step instructions to deploy your competitive intelligence system to production with proper monitoring, alerting, and backup strategies.

## Prerequisites
- Docker and Docker Compose installed
- PostgreSQL 15+ (local or cloud managed)
- Python 3.11+
- Access to cloud provider (AWS/GCP/Azure)
- OpenAI API key (for AI summarization)
- Slack webhook URL (for alerts)

## 1. Database Initialization (Fresh Environment)

### Local PostgreSQL Setup
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database user and database
sudo -u postgres psql -c "CREATE USER competitive_intel WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE competitive_intelligence OWNER competitive_intel;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE competitive_intelligence TO competitive_intel;"
```

### Environment Configuration
```bash
# Copy environment template
cp .env.production.example .env

# Edit .env with your actual values
nano .env

# Required variables:
DB_HOST=localhost
DB_NAME=competitive_intelligence
DB_USER=competitive_intel
DB_PASSWORD=your_secure_password
SECRET_KEY=your_super_secret_key_here
OPENAI_API_KEY=your_openai_api_key
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### Initialize Database Schema
```bash
# Make the script executable
chmod +x init_production_db.sh

# Run initialization script
./init_production_db.sh
```

### Alternative: Using Python Setup Script
```bash
python setup_postgres.py
```

## 2. Local Development & Testing

### Setup Virtual Environment
```bash
# Make setup script executable
chmod +x setup_local.sh

# Run local setup
./setup_local.sh

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Test the Application
```bash
# Run development server
python app_postgres.py

# Test in another terminal
curl http://localhost:5000/health
curl http://localhost:5000/
```

### Run with Production Server (Gunicorn)
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 app_postgres:app

# Test production setup
curl http://localhost:8000/health
```

## 3. AI Summarization Integration

### Setup AI Service
The AI summarization is automatically integrated into the approval workflow. Configure in your environment:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export OPENAI_MODEL="gpt-4-turbo-preview"
export MAX_SUMMARY_LENGTH=500
```

### Test AI Integration
```bash
python ai_summarization.py
```

### Integration in Flask App
The AI summarization automatically triggers when new content is added to the `raw_fetch_queue`. To manually trigger:

```python
from ai_summarization import integrate_ai_summarization
integrate_ai_summarization()
```

## 4. Alerting Configuration

### Slack Setup
1. Create a Slack app at https://api.slack.com/apps
2. Create an incoming webhook
3. Add webhook URL to `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Email Setup (Gmail example)
```bash
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password  # Use App Password for Gmail
EMAIL_FROM=alerts@yourcompany.com
EMAIL_TO=pm@yourcompany.com,analyst@yourcompany.com
```

### Test Alerting
```bash
python alerting_service.py
```

## 5. Docker Deployment

### Build and Run with Docker Compose
```bash
# Create necessary directories
mkdir -p logs nginx/ssl

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
docker-compose logs app

# Test the deployment
curl http://localhost/health
```

### Check Container Health
```bash
# View logs
docker-compose logs -f app
docker-compose logs -f postgres

# Check resource usage
docker stats

# Access application container
docker-compose exec app /bin/bash
```

### Production Docker Commands
```bash
# Build production image
docker build -t competitive-intel:latest .

# Run with specific environment
docker run -d \
  --name competitive-intel-app \
  --env-file .env \
  -p 8000:8000 \
  competitive-intel:latest

# Database migration (if needed)
docker-compose exec app python setup_postgres.py
```

## 6. Cloud Deployment (AWS Example)

### Prerequisites
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
```

### Deploy with ECS Fargate
1. **Create ECR Repository**
```bash
aws ecr create-repository --repository-name competitive-intel-app
```

2. **Build and Push Docker Image**
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Tag and push image
docker tag competitive-intel:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/competitive-intel-app:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/competitive-intel-app:latest
```

3. **Create RDS PostgreSQL Instance**
```bash
aws rds create-db-instance \
  --db-instance-identifier competitive-intel-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --allocated-storage 100 \
  --db-name competitive_intelligence \
  --master-username postgres \
  --master-user-password YOUR_DB_PASSWORD \
  --vpc-security-group-ids sg-YOUR_SECURITY_GROUP \
  --backup-retention-period 7 \
  --storage-encrypted
```

4. **Deploy ECS Service** (Use provided task definition)

### Alternative: Deploy to AWS App Runner
```bash
# Create apprunner.yaml
echo 'version: 1.0
runtime: docker
build:
  commands:
    build:
      - echo "No build commands"
run:
  runtime-version: latest
  command: gunicorn --bind 0.0.0.0:8000 --workers 4 app_postgres:app
  network:
    port: 8000
    env: PORT
' > apprunner.yaml

# Deploy via AWS Console or CLI
```

## 7. Monitoring and Logging Best Practices

### Application Monitoring
```bash
# View application logs
tail -f logs/app.log

# Monitor metrics
curl http://localhost:8000/metrics

# Check detailed health
curl http://localhost:8000/health/detailed
```

### Database Monitoring
```bash
# Monitor database performance
python -c "
from production_monitoring import setup_logging, setup_performance_monitoring
from app_postgres import app, db
setup_logging(app)
setup_performance_monitoring(app)
"

# Check existing monitoring dashboard
python monitoring.py
```

### Set up Log Rotation
```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/competitive-intel << EOF
/path/to/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 appuser appuser
}
EOF
```

### Production Monitoring Setup
1. **Prometheus + Grafana** (Recommended)
```bash
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

2. **CloudWatch (AWS)**
```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U ./amazon-cloudwatch-agent.rpm
```

## 8. Backup and Recovery

### Database Backup Strategy
```bash
# Automated daily backup script
#!/bin/bash
# backup_db.sh
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="competitive_intel_backup_$DATE.sql"

mkdir -p $BACKUP_DIR

pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/$BACKUP_FILE
gzip $BACKUP_DIR/$BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### Setup Cron Job
```bash
# Add to crontab
crontab -e

# Add this line (daily backup at 2 AM)
0 2 * * * /path/to/backup_db.sh >> /var/log/db_backup.log 2>&1
```

### AWS RDS Automated Backup
```bash
# Enable automated backups (already included in RDS creation command)
aws rds modify-db-instance \
  --db-instance-identifier competitive-intel-db \
  --backup-retention-period 7 \
  --apply-immediately
```

## 9. Security Checklist

### Application Security
- [ ] Use strong, unique SECRET_KEY
- [ ] Enable HTTPS in production
- [ ] Set up proper CORS policies
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting (configured in nginx)
- [ ] Regular dependency updates

### Database Security
- [ ] Use strong database passwords
- [ ] Enable SSL connections
- [ ] Restrict database access to application only
- [ ] Regular security updates
- [ ] Monitor for suspicious activity

### Infrastructure Security
- [ ] Use security groups/firewalls
- [ ] Enable logging and monitoring
- [ ] Regular OS updates
- [ ] Use secrets management service
- [ ] Implement backup encryption

## 10. Maintenance Tasks

### Weekly Tasks
```bash
# Check system health
curl http://localhost:8000/health/detailed

# Review logs for errors
grep -i error logs/app.log | tail -20

# Monitor resource usage
docker stats

# Check database performance
python monitoring.py
```

### Monthly Tasks
```bash
# Update dependencies
pip list --outdated
pip install -r requirements.txt --upgrade

# Review and rotate logs
sudo logrotate -f /etc/logrotate.d/competitive-intel

# Database maintenance
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Review backup retention
ls -la /backups/postgres/
```

### Quarterly Tasks
- Security audit and dependency updates
- Performance optimization review
- Backup and recovery testing
- Disaster recovery plan review
- Cost optimization review (cloud deployments)

## 11. Troubleshooting

### Common Issues

**Database Connection Issues**
```bash
# Test database connectivity
pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER

# Check connection pool
curl http://localhost:8000/health/detailed
```

**High Memory Usage**
```bash
# Check memory usage
docker stats
htop

# Optimize database connections
# Reduce worker count in gunicorn
gunicorn --workers 2 --bind 0.0.0.0:8000 app_postgres:app
```

**Slow Performance**
```bash
# Check database performance
python -c "
from production_monitoring import DatabaseMonitor
from app_postgres import db
monitor = DatabaseMonitor(db)
monitor.check_slow_queries()
"

# Check application metrics
curl http://localhost:8000/metrics
```

## 12. Support and Maintenance

### Log Analysis
```bash
# Parse structured logs
cat logs/app.log | jq '.message' | grep -i error

# Monitor request patterns
cat logs/app.log | jq '.url' | sort | uniq -c | sort -nr
```

### Performance Optimization
- Monitor and optimize database queries
- Implement caching for frequent requests
- Use CDN for static assets
- Consider horizontal scaling for high load

### Scaling Considerations
- Database read replicas for read-heavy workloads
- Load balancer for multiple application instances
- Redis for session storage and caching
- Queue system for background processing

This completes your production deployment guide. The system is now ready for enterprise-scale competitive intelligence operations with proper monitoring, alerting, and backup strategies.
