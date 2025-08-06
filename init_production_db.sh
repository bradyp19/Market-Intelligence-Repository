#!/bin/bash
# Production Database Initialization Script
# Run this in a fresh environment to set up the PostgreSQL database

set -e  # Exit on any error

echo "🚀 Initializing Competitive Intelligence Database..."

# Check if environment variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "❌ Missing required environment variables. Please set:"
    echo "   DB_HOST, DB_NAME, DB_USER, DB_PASSWORD"
    exit 1
fi

echo "📋 Database Configuration:"
echo "   Host: $DB_HOST"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo ""

# Install PostgreSQL client if not available (Ubuntu/Debian)
if ! command -v psql &> /dev/null; then
    echo "📦 Installing PostgreSQL client..."
    sudo apt-get update && sudo apt-get install -y postgresql-client
fi

# Test connection to PostgreSQL server
echo "🔌 Testing PostgreSQL connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d postgres -c "SELECT version();" > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL connection successful"
else
    echo "❌ Failed to connect to PostgreSQL server"
    exit 1
fi

# Create database if it doesn't exist
echo "🗄️  Creating database '$DB_NAME'..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1 || PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE \"$DB_NAME\";"

# Apply schema
echo "📝 Applying database schema..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql

# Verify tables were created
echo "🔍 Verifying table creation..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✅ Database initialized successfully with $TABLE_COUNT tables"
    echo "📊 Tables created:"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\dt"
else
    echo "❌ No tables found. Schema application may have failed."
    exit 1
fi

echo ""
echo "🎉 Database initialization complete!"
echo "💡 Next steps:"
echo "   1. Set up your .env file with the database credentials"
echo "   2. Install Python dependencies: pip install -r requirements.txt"
echo "   3. Run the Flask app: python app_postgres.py"
