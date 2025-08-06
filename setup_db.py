#!/usr/bin/env python3
"""
Setup database tables using SQLAlchemy.
Run this script to create all tables defined in the Flask models.
"""

import os
from app_postgres import app, db

def setup_database():
    """Create all database tables."""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")

if __name__ == '__main__':
    setup_database()
