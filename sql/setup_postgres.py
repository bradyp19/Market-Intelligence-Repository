#!/usr/bin/env python3
"""
Setup PostgreSQL database for competitive intelligence system.
Run this script to create the database, apply the schema, and insert initial data.
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'competitive_intelligence')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

def create_database():
    """Create the database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server (not to a specific database)
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"✅ Created database '{DB_NAME}'")
        else:
            print(f"ℹ️  Database '{DB_NAME}' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error creating database: {e}")
        return False

def apply_schema():
    """Apply the schema from schema.sql file."""
    try:
        # Connect to the competitive intelligence database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Read and execute schema file
        schema_file = 'schema.sql'
        if os.path.exists(schema_file):
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Execute the schema
            cursor.execute(schema_sql)
            print("✅ Applied database schema successfully")
        else:
            print(f"❌ Schema file '{schema_file}' not found")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error applying schema: {e}")
        return False

def test_connection():
    """Test the database connection and show some basic info."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # Test queries
        cursor.execute("SELECT COUNT(*) FROM competitors")
        competitor_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        print(f"✅ Database connection successful!")
        print(f"   - Competitors: {competitor_count}")
        print(f"   - Users: {user_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error testing connection: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up PostgreSQL database for Competitive Intelligence System")
    print("="*70)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  .env file not found. Please create one based on .env.example")
        print("   Required variables: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        return False
    
    # Step 1: Create database
    print("1️⃣  Creating database...")
    if not create_database():
        return False
    
    # Step 2: Apply schema
    print("2️⃣  Applying database schema...")
    if not apply_schema():
        return False
    
    # Step 3: Test connection
    print("3️⃣  Testing database connection...")
    if not test_connection():
        return False
    
    print("="*70)
    print("🎉 Database setup completed successfully!")
    print(f"   Database: {DB_NAME}")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   User: {DB_USER}")
    print()
    print("Next steps:")
    print("   1. Run: python app_postgres.py")
    print("   2. Visit: http://localhost:5000")
    print("   3. Start scraping competitive intelligence!")
    
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        exit(1)
