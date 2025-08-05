from flask import Flask, render_template, redirect, url_for
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
    # New fields for PM workflow
    status = db.Column(db.String(50), default='new') # 'new', 'reviewed', 'archived'
    pm_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Article {self.company} - {self.title[:50]}>'

# --- Routes ---
@app.route('/')
def index():
    """Main dashboard showing new and reviewed articles."""
    new_articles = Article.query.filter_by(status='new').order_by(Article.confidence_score.desc()).all()
    reviewed_articles = Article.query.filter_by(status='reviewed').order_by(Article.id.desc()).all()
    return render_template('index.html', new_articles=new_articles, reviewed_articles=reviewed_articles)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create tables if they don't exist
    app.run(debug=True)
