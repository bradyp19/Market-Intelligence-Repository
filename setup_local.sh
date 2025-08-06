#!/bin/bash
# Local Development Setup and Testing Script

set -e

echo "🚀 Setting up Competitive Intelligence App locally..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python version: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.production.example .env
    echo "❗ Please edit .env file with your actual configuration before running the app"
fi

# Load environment variables
source .env

# Check PostgreSQL connection
echo "🔌 Testing database connection..."
python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port='$DB_PORT',
        user='$DB_USER',
        password='$DB_PASSWORD',
        database='$DB_NAME'
    )
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Initialize database if needed
echo "🗄️  Initializing database..."
python3 setup_postgres.py

# Run basic app test
echo "🧪 Testing Flask app initialization..."
python3 -c "
from app_postgres import app, db
with app.app_context():
    print('✅ Flask app initialized successfully')
    print(f'Database URI: {app.config[\"SQLALCHEMY_DATABASE_URI\"][:50]}...')
"

echo ""
echo "🎉 Local setup complete!"
echo ""
echo "📋 To start the development server:"
echo "   source venv/bin/activate"
echo "   python app_postgres.py"
echo ""
echo "🌐 The app will be available at http://localhost:5000"
echo ""
echo "🔍 To run in production mode:"
echo "   gunicorn --bind 0.0.0.0:8000 --workers 4 app_postgres:app"
