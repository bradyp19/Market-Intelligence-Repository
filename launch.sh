#!/bin/bash
# Quick launch script for Competitive Intelligence App

echo "🚀 Competitive Intelligence System - Quick Launch"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Check what launch method to use
if [ "$1" = "docker" ]; then
    echo "🐳 Starting with Docker..."
    cd deployment/docker
    docker-compose up -d
    echo ""
    echo "✅ Services started! Available at:"
    echo "   🌐 Web App: http://localhost"
    echo "   💾 Database: localhost:5432"
    echo "   📊 Redis: localhost:6379"
    echo ""
    echo "📋 Useful commands:"
    echo "   docker-compose logs -f app    # View app logs"
    echo "   docker-compose ps             # Check service status"
    echo "   docker-compose down           # Stop services"
    
elif [ "$1" = "local" ] || [ -z "$1" ]; then
    echo "💻 Starting local development..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "📦 Setting up development environment..."
        cd deployment/scripts
        chmod +x setup_local.sh
        ./setup_local.sh
        cd ../..
    fi
    
    # Activate virtual environment and start app
    source venv/bin/activate
    echo "🔧 Starting Flask development server..."
    export PYTHONPATH="src:$PYTHONPATH"
    python src/app_postgres.py
    
else
    echo "❓ Usage:"
    echo "   ./launch.sh          # Local development (default)"
    echo "   ./launch.sh local    # Local development"
    echo "   ./launch.sh docker   # Docker deployment"
    exit 1
fi
