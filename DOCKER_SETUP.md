# Docker Setup Instructions

This document provides step-by-step instructions for running the Competitive Intelligence Flask application with PostgreSQL using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

## Quick Start

### 1. Build and Start Services

```bash
docker-compose up --build
```

This command will:
- Build the Flask application Docker image
- Start PostgreSQL database service
- Start the Flask application service
- Create necessary volumes for data persistence

### 2. Initialize Database (First Run Only)

Before the application can work properly, you need to create the database tables:

```bash
docker-compose run app python setup_db.py
```

### 3. Access the Application

- **Application**: http://localhost:5000
- **Health Check**: http://localhost:5000/health

## Detailed Steps

### Step 1: Environment Configuration

The `.env` file is already configured for Docker. Key settings:

```env
USE_SQLITE=false
DB_HOST=db
DB_PORT=5432
DB_NAME=competitive_intelligence
DB_USER=postgres
DB_PASSWORD=postgres
```

### Step 2: Build and Run

```bash
# Build and start in foreground
docker-compose up --build

# Or run in background (detached mode)
docker-compose up --build -d
```

### Step 3: Database Setup

Run the database initialization script:

```bash
docker-compose run app python setup_db.py
```

This creates all the necessary tables defined in your Flask models.

### Step 4: Verify Setup

Check that everything is running:

```bash
# Check running containers
docker-compose ps

# Check application health
curl http://localhost:5000/health

# View logs
docker-compose logs app
docker-compose logs db
```

## Container Services

### Database Service (`db`)
- **Image**: postgres:15
- **Port**: 5432 (internal)
- **Volume**: `postgres_data` for data persistence
- **Health Check**: `pg_isready` command

### Application Service (`app`)
- **Build**: From local Dockerfile
- **Port**: 5000:5000 (host:container)
- **Dependencies**: Waits for database health check
- **Health Check**: HTTP GET `/health`

## Management Commands

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Volumes (⚠️ Data Loss)
```bash
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs app
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f app
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild Application
```bash
docker-compose build app
docker-compose up app
```

### Execute Commands in Containers
```bash
# Access application container shell
docker-compose exec app bash

# Access database container
docker-compose exec db psql -U postgres -d competitive_intelligence

# Run Python scripts
docker-compose run app python your_script.py
```

## Troubleshooting

### Database Connection Issues
1. Ensure the database service is healthy:
   ```bash
   docker-compose ps
   ```

2. Check database logs:
   ```bash
   docker-compose logs db
   ```

3. Test database connectivity:
   ```bash
   docker-compose exec db pg_isready -U postgres
   ```

### Application Issues
1. Check application logs:
   ```bash
   docker-compose logs app
   ```

2. Verify health endpoint:
   ```bash
   curl http://localhost:5000/health
   ```

3. Check if tables exist:
   ```bash
   docker-compose exec db psql -U postgres -d competitive_intelligence -c "\dt"
   ```

### Port Conflicts
If port 5000 is already in use, modify the `docker-compose.yml`:

```yaml
services:
  app:
    ports:
      - "8080:5000"  # Use port 8080 instead
```

## Development Workflow

### Making Code Changes
1. Edit your code files
2. Rebuild and restart:
   ```bash
   docker-compose up --build
   ```

### Database Schema Changes
1. Update your Flask models
2. Recreate containers:
   ```bash
   docker-compose down
   docker-compose up --build
   docker-compose run app python setup_db.py
   ```

## Production Considerations

For production deployment:

1. **Environment Variables**: Use production values in `.env`
2. **Secret Key**: Generate a secure `SECRET_KEY`
3. **Database Password**: Use a strong `DB_PASSWORD`
4. **SSL**: Add SSL certificate configuration
5. **Reverse Proxy**: Consider adding nginx for load balancing
6. **Monitoring**: Add logging and monitoring services

## File Structure

```
├── Dockerfile              # Flask app container definition
├── docker-compose.yml      # Multi-service orchestration
├── .env                    # Environment configuration
├── setup_db.py            # Database initialization script
├── app_postgres.py         # Main Flask application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```
