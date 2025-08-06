#!/bin/bash
# Cleanup script for development environment

echo "🧹 Cleaning up Competitive Intelligence development environment..."

# Clean Python cache
echo "🗑️  Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Clean logs
echo "📄 Cleaning log files..."
if [ -d "logs" ]; then
    rm -f logs/*.log
    echo "   Cleared application logs"
fi

# Clean temporary files
echo "🔧 Removing temporary files..."
rm -f .DS_Store
rm -f Thumbs.db
rm -f *.tmp
rm -f *.bak

# Clean Docker resources (if requested)
if [ "$1" = "docker" ] || [ "$1" = "all" ]; then
    echo "🐳 Cleaning Docker resources..."
    cd deployment/docker
    docker-compose down -v --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
    cd ../..
    echo "   Docker containers and volumes removed"
fi

# Clean virtual environment (if requested)
if [ "$1" = "venv" ] || [ "$1" = "all" ]; then
    echo "🗂️  Removing virtual environment..."
    rm -rf venv/
    echo "   Virtual environment removed"
fi

# Clean database files (if requested)
if [ "$1" = "db" ] || [ "$1" = "all" ]; then
    echo "💾 Cleaning database files..."
    rm -f metrics.db
    rm -rf instance/
    echo "   Local database files removed"
fi

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "💡 Usage options:"
echo "   ./cleanup.sh          # Basic cleanup (cache, logs, temp)"
echo "   ./cleanup.sh docker   # Also remove Docker containers/volumes"
echo "   ./cleanup.sh venv     # Also remove virtual environment"
echo "   ./cleanup.sh db       # Also remove local database files"
echo "   ./cleanup.sh all      # Complete cleanup (everything above)"
