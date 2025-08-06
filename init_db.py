#!/usr/bin/env python3
"""
Initialize the database with proper schema for the enhanced triage system.
"""

from app import app, db, Article
import os

def init_database():
    """Initialize the database with the correct schema."""
    with app.app_context():
        # Remove existing database if it exists
        if os.path.exists('market_intelligence.db'):
            os.remove('market_intelligence.db')
            print("Removed existing database")
        
        # Create all tables
        db.create_all()
        print("Created new database with updated schema")
        
        # Verify the schema
        import sqlite3
        conn = sqlite3.connect('market_intelligence.db')
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(article)')
        columns = cursor.fetchall()
        print("Article table columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        conn.close()

if __name__ == '__main__':
    init_database()
