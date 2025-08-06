#!/usr/bin/env python3
"""
Flask application for competitive intelligence system using PostgreSQL.
"""

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, and_, or_
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.exc import IntegrityError
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App initialization
app = Flask(__name__)

# PostgreSQL configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'competitive_intelligence')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Database initialization
db = SQLAlchemy(app)

# Models based on PostgreSQL schema
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

class Competitor(db.Model):
    __tablename__ = 'competitors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    domain = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

class RawFetchQueue(db.Model):
    __tablename__ = 'raw_fetch_queue'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    processed_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    rejection_reason = db.Column(db.Text)
    meta_info = db.Column(db.JSON, default={})
    
    # Relationships
    competitor = db.relationship('Competitor', backref='raw_fetches')
    processor = db.relationship('User', backref='processed_fetches')

class CompetitorUpdate(db.Model):
    __tablename__ = 'competitor_updates'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'), nullable=False)
    raw_fetch_id = db.Column(UUID(as_uuid=True), db.ForeignKey('raw_fetch_queue.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text)
    url = db.Column(db.String(1000), nullable=False)
    published_date = db.Column(db.DateTime(timezone=True), nullable=False)
    relevance_category = db.Column(db.String(50))
    strategic_priority = db.Column(db.String(10), default='medium')
    confidence_score = db.Column(db.Numeric(5, 2), nullable=False)
    approved_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    approved_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    pm_notes = db.Column(db.Text)
    ai_summary = db.Column(db.Text)
    tags = db.Column(ARRAY(db.String), default=[])
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # Relationships
    competitor = db.relationship('Competitor', backref='updates')
    raw_fetch = db.relationship('RawFetchQueue', backref='approved_updates')
    approver = db.relationship('User', backref='approved_updates')

# Routes
@app.route('/')
def index():
    """Main dashboard showing triage queue and recent approvals."""
    # Get pending items for triage
    pending_query = db.session.query(RawFetchQueue, Competitor).join(
        Competitor, RawFetchQueue.competitor_id == Competitor.id
    ).filter(RawFetchQueue.status == 'pending').order_by(
        RawFetchQueue.confidence_score.desc(),
        RawFetchQueue.fetched_at.desc()
    ).limit(20)
    
    # Get recent approved items
    approved_query = db.session.query(CompetitorUpdate, Competitor, User).join(
        Competitor, CompetitorUpdate.competitor_id == Competitor.id
    ).join(
        User, CompetitorUpdate.approved_by == User.id
    ).filter(
        CompetitorUpdate.is_archived == False
    ).order_by(CompetitorUpdate.approved_at.desc()).limit(20)
    
    # Count high priority items
    high_priority_count = CompetitorUpdate.query.filter(
        and_(
            CompetitorUpdate.strategic_priority == 'high',
            CompetitorUpdate.is_archived == False
        )
    ).count()
    
    pending_items = pending_query.all()
    approved_items = approved_query.all()
    
    return render_template('dashboard.html', 
                         pending_items=pending_items,
                         approved_items=approved_items,
                         high_priority_count=high_priority_count)

@app.route('/run_scraper')
def run_scraper_route():
    """Run the scraper and add new items to the queue."""
    try:
        # Import scraper here to avoid circular imports
        from scraper import AnnouncementScraper
        
        scraper = AnnouncementScraper()
        new_items_count = 0
        
        # Get all active competitors
        competitors = Competitor.query.filter_by(is_active=True).all()
        
        for competitor in competitors:
            # This is a simplified version - you'd integrate with your existing scraper
            company_data = scraper.scrape_company(competitor.name.lower())
            
            for article_data in company_data:
                # Check for duplicates
                existing = RawFetchQueue.query.filter_by(url=article_data['url']).first()
                if not existing:
                    new_item = RawFetchQueue(
                        competitor_id=competitor.id,
                        url=article_data['url'],
                        title=article_data['title'],
                        content=article_data['text'],
                        confidence_score=article_data.get('confidence_score', 50.0),
                        published_date=article_data.get('date'),
                        meta_info={'source': 'web_scraper'}
                    )
                    db.session.add(new_item)
                    new_items_count += 1
        
        db.session.commit()
        flash(f'Successfully added {new_items_count} new items to the queue', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error during scraping: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/triage/<uuid:item_id>/<action>')
def triage_item(item_id, action):
    """Handle triage actions for raw fetch items."""
    item = RawFetchQueue.query.get_or_404(item_id)
    
    # Get default user (in production, this would come from authentication)
    default_user = User.query.filter_by(role='product_manager').first()
    if not default_user:
        flash('No product manager user found', 'error')
        return redirect(url_for('index'))
    
    if action == 'approve':
        # Move to approved updates
        approved_update = CompetitorUpdate(
            competitor_id=item.competitor_id,
            raw_fetch_id=item.id,
            title=item.title,
            summary=item.content[:500] + '...' if item.content and len(item.content) > 500 else item.content,
            url=item.url,
            published_date=item.published_date or item.fetched_at,
            confidence_score=item.confidence_score,
            approved_by=default_user.id,
            strategic_priority='medium'
        )
        
        item.status = 'approved'
        item.processed_at = datetime.now(timezone.utc)
        item.processed_by = default_user.id
        
        db.session.add(approved_update)
        flash('Item approved and added to competitive intelligence', 'success')
        
    elif action == 'reject':
        item.status = 'rejected'
        item.processed_at = datetime.now(timezone.utc)
        item.processed_by = default_user.id
        flash('Item rejected', 'info')
        
    elif action == 'archive':
        item.status = 'archived'
        item.processed_at = datetime.now(timezone.utc)
        item.processed_by = default_user.id
        flash('Item archived', 'info')
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing item: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/categorize/<uuid:update_id>/<category>')
def categorize_update(update_id, category):
    """Set the relevance category for an approved update."""
    update = CompetitorUpdate.query.get_or_404(update_id)
    
    valid_categories = ['product_launch', 'partnership', 'strategy', 'acquisition', 'funding', 'other']
    if category in valid_categories:
        update.relevance_category = category
        update.updated_at = datetime.now(timezone.utc)
        
        try:
            db.session.commit()
            flash(f'Category set to {category.replace("_", " ").title()}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/priority/<uuid:update_id>/<priority>')
def set_priority(update_id, priority):
    """Set the strategic priority for an approved update."""
    update = CompetitorUpdate.query.get_or_404(update_id)
    
    valid_priorities = ['high', 'medium', 'low']
    if priority in valid_priorities:
        update.strategic_priority = priority
        update.updated_at = datetime.now(timezone.utc)
        
        try:
            db.session.commit()
            flash(f'Priority set to {priority.title()}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating priority: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics."""
    stats = {
        'pending_count': RawFetchQueue.query.filter_by(status='pending').count(),
        'approved_count': CompetitorUpdate.query.filter_by(is_archived=False).count(),
        'high_priority_count': CompetitorUpdate.query.filter(
            and_(CompetitorUpdate.strategic_priority == 'high',
                 CompetitorUpdate.is_archived == False)
        ).count(),
        'total_competitors': Competitor.query.filter_by(is_active=True).count()
    }
    return jsonify(stats)

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        
        # Get basic system stats
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'connected',
            'version': '1.0.0'
        }
        
        # Optional: Add more health checks
        pending_count = RawFetchQueue.query.filter_by(status='pending').count()
        if pending_count > 1000:  # Adjust threshold as needed
            health_status['warnings'] = [f'High pending queue: {pending_count} items']
        
        return jsonify(health_status), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }), 503

if __name__ == '__main__':
    app.run(debug=True, port=5000)
