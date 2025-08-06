from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os
from scraper import AnnouncementScraper

# App initialization
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market_intelligence.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), unique=True, nullable=False)
    text = db.Column(db.Text, nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    publication_date = db.Column(db.DateTime, nullable=True)
    
    # Enhanced triage workflow fields
    status = db.Column(db.String(50), default='pending') # 'pending', 'approved', 'rejected', 'archived'
    relevance_category = db.Column(db.String(50), nullable=True) # 'product_launch', 'partnership', 'strategy', 'pricing', 'other'
    strategic_priority = db.Column(db.String(20), default='medium') # 'high', 'medium', 'low'
    
    # Review tracking
    reviewer_id = db.Column(db.String(100), nullable=True)
    review_date = db.Column(db.DateTime, nullable=True)
    pm_notes = db.Column(db.Text, nullable=True)
    
    # Auto-generated strategic summary (we'll add this next)
    ai_summary = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Article {self.company} - {self.title[:50]}>'

# --- Routes ---
@app.route('/')
def index():
    """Main dashboard showing pending items for triage and approved strategic intelligence."""
    # Pending items that need triage (sorted by confidence score - highest first)
    pending_articles = Article.query.filter_by(status='pending').order_by(Article.confidence_score.desc()).all()
    
    # Approved strategic intelligence (most recent first)
    approved_articles = Article.query.filter_by(status='approved').order_by(Article.review_date.desc()).limit(20).all()
    
    # High priority items that need immediate attention (confidence > 80)
    high_priority_count = Article.query.filter(
        Article.status == 'pending',
        Article.confidence_score >= 80
    ).count()
    
    return render_template('index.html', 
                         pending_articles=pending_articles,
                         approved_articles=approved_articles,
                         high_priority_count=high_priority_count)

@app.route('/run_scraper')
def run_scraper_route():
    """Endpoint to trigger the scraper and save results to the database."""
    print("Scraping started...")
    
    try:
        # Initialize the scraper
        scraper = AnnouncementScraper()
        
        # Run the scraper for all companies
        scraped_data = scraper.scrape_all_companies()
        
        new_articles_count = 0
        
        # Process the results
        for company, articles in scraped_data.items():
            print(f"Processing {len(articles)} articles for {company}")
            
            for article_data in articles:
                # Check if an article with the same URL already exists
                existing_article = Article.query.filter_by(url=article_data['url']).first()
                
                if not existing_article:
                    # Create new article
                    new_article = Article(
                        company=company,
                        title=article_data.get('title', 'No Title'),
                        url=article_data.get('url'),
                        text=article_data.get('text', ''),
                        confidence_score=article_data.get('confidence_score', 0.0),
                        publication_date=article_data.get('date')
                    )
                    
                    db.session.add(new_article)
                    new_articles_count += 1
        
        # Commit all changes
        db.session.commit()
        print(f"Scraping finished. Added {new_articles_count} new articles to database.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during scraping: {str(e)}")
    
    return redirect(url_for('index'))

@app.route('/triage/<int:article_id>/<action>')
def triage_article(article_id, action):
    """Handle triage actions for articles."""
    from datetime import datetime
    
    article = Article.query.get_or_404(article_id)
    
    if action == 'approve':
        article.status = 'approved'
        article.strategic_priority = 'medium'  # Default, can be changed later
    elif action == 'reject':
        article.status = 'rejected'
    elif action == 'archive':
        article.status = 'archived'
    
    article.review_date = datetime.now()
    # In a real system, you'd get this from authentication
    article.reviewer_id = 'product_manager'  
    
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/categorize/<int:article_id>/<category>')
def categorize_article(article_id, category):
    """Categorize an approved article."""
    article = Article.query.get_or_404(article_id)
    
    valid_categories = ['product_launch', 'partnership', 'strategy', 'acquisition', 'funding', 'other']
    if category in valid_categories:
        article.relevance_category = category
        db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/priority/<int:article_id>/<priority>')
def set_priority(article_id, priority):
    """Set strategic priority for an article."""
    article = Article.query.get_or_404(article_id)
    
    valid_priorities = ['high', 'medium', 'low']
    if priority in valid_priorities:
        article.strategic_priority = priority
        db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/add_notes/<int:article_id>', methods=['GET', 'POST'])
def add_notes(article_id):
    """Add strategic notes to an article."""
    from datetime import datetime
    
    article = Article.query.get_or_404(article_id)
    if request.method == 'POST':
        notes = request.form.get('notes', '')
        article.pm_notes = notes
        article.reviewer_id = 'product_manager'
        article.review_date = datetime.now()
        db.session.commit()
        return redirect(url_for('index'))
    
    return f"""
    <html>
    <head><title>Add Strategic Notes</title></head>
    <body style="font-family: sans-serif; margin: 2em;">
        <h2>Add Strategic Notes</h2>
        <h3>{article.title}</h3>
        <p><strong>Company:</strong> {article.company}</p>
        <form method="POST">
            <textarea name="notes" placeholder="Add strategic notes for roadmap planning..." rows="6" cols="60" style="width: 100%; max-width: 500px;">{article.pm_notes or ''}</textarea><br><br>
            <input type="submit" value="Save Notes" style="background: #4caf50; color: white; padding: 0.5em 1em; border: none; border-radius: 4px;">
            <a href="{url_for('index')}" style="margin-left: 1em; color: #666;">Cancel</a>
        </form>
    </body>
    </html>
    """

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create tables if they don't exist
    app.run(debug=True)
