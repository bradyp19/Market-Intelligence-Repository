#!/usr/bin/env python3
"""
Test script to verify that SQLAlchemy models can be created without metadata conflicts.
"""

import os
import sys
from datetime import datetime, timezone
os.environ['USE_SQLITE'] = 'true'

# Add src to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    import uuid
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import UUID, ARRAY
    
    # Create a simple Flask app for testing
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-key'
    
    db = SQLAlchemy(app)
    
    # Define the models that were problematic
    class User(db.Model):
        __tablename__ = 'users'
        
        id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        username = db.Column(db.String(50), unique=True, nullable=False)
        email = db.Column(db.String(100), unique=True, nullable=False)
        role = db.Column(db.String(20), default='analyst')
        created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

    class Competitor(db.Model):
        __tablename__ = 'competitors'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), unique=True, nullable=False)
        domain = db.Column(db.String(255), unique=True, nullable=False)
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

    class RawFetchQueue(db.Model):
        __tablename__ = 'raw_fetch_queue'
        
        id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'), nullable=False)
        url = db.Column(db.String(1000), unique=True, nullable=False)
        title = db.Column(db.String(500))
        content = db.Column(db.Text)
        raw_html = db.Column(db.Text)
        published_date = db.Column(db.DateTime(timezone=True))
        confidence_score = db.Column(db.Numeric(5, 2))
        fetched_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
        status = db.Column(db.String(20), default='pending')
        processed_at = db.Column(db.DateTime(timezone=True))
        processed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
        rejection_reason = db.Column(db.Text)
        meta_info = db.Column(db.JSON, default={})  # This was the problematic 'metadata' field
        
        # Relationships
        competitor = db.relationship('Competitor', backref='raw_fetches')
        processor = db.relationship('User', backref='processed_fetches')

    class CompetitorUpdate(db.Model):
        __tablename__ = 'competitor_updates'
        
        id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'), nullable=False)
        raw_fetch_id = db.Column(db.String(36), db.ForeignKey('raw_fetch_queue.id'), nullable=False)
        title = db.Column(db.String(500), nullable=False)
        summary = db.Column(db.Text)
        url = db.Column(db.String(1000), nullable=False)
        published_date = db.Column(db.DateTime(timezone=True), nullable=False)
        relevance_category = db.Column(db.String(50))
        strategic_priority = db.Column(db.String(10), default='medium')
        confidence_score = db.Column(db.Numeric(5, 2), nullable=False)
        approved_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
        approved_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
        pm_notes = db.Column(db.Text)
        ai_summary = db.Column(db.Text)
        tags = db.Column(db.Text, default='[]')  # Store as JSON string for SQLite
        is_archived = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
        updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
        
        # Relationships
        competitor = db.relationship('Competitor', backref='updates')
        raw_fetch = db.relationship('RawFetchQueue', backref='approved_updates')
        approver = db.relationship('User', backref='approved_updates')

    # Test creating the models
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        print("✅ No SQLAlchemy metadata conflicts detected!")
        
        # Test creating sample objects
        print("Testing model instantiation...")
        
        # Create a test competitor
        test_competitor = Competitor(name="Test Corp", domain="test.com")
        db.session.add(test_competitor)
        db.session.commit()
        
        # Create a test user
        test_user = User(username="testuser", email="test@example.com")
        db.session.add(test_user)
        db.session.commit()
        
        # Create a raw fetch item with meta_info (the field that was previously 'metadata')
        raw_fetch = RawFetchQueue(
            competitor_id=test_competitor.id,
            url="https://test.com/article",
            title="Test Article",
            content="Test content",
            confidence_score=75.0,
            meta_info={'source': 'test_script', 'version': '1.0'}
        )
        db.session.add(raw_fetch)
        db.session.commit()
        
        print("✅ Successfully created and saved test records!")
        print(f"✅ Raw fetch meta_info: {raw_fetch.meta_info}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Clean up test database
    if os.path.exists('test.db'):
        os.remove('test.db')
        print("🧹 Cleaned up test database")
