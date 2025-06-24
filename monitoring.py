"""
Monitoring and metrics module for the Market Intelligence Agent.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import sqlite3
from dataclasses import dataclass, asdict
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingMetrics:
    """Metrics for scraping operations."""
    company: str
    url: str
    status: str
    latency: float
    content_length: int
    error_message: Optional[str] = None
    timestamp: datetime = datetime.now()

@dataclass
class SummaryMetrics:
    """Metrics for summary generation."""
    company: str
    url: str
    latency: float
    confidence_score: float
    needs_review: bool
    error_message: Optional[str] = None
    timestamp: datetime = datetime.now()

class MetricsCollector:
    def __init__(self, db_path: str = 'metrics.db'):
        """Initialize metrics collector with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create scraping metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scraping_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company TEXT,
                        url TEXT,
                        status TEXT,
                        latency REAL,
                        content_length INTEGER,
                        error_message TEXT,
                        timestamp DATETIME
                    )
                ''')
                
                # Create summary metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS summary_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company TEXT,
                        url TEXT,
                        latency REAL,
                        confidence_score REAL,
                        needs_review BOOLEAN,
                        error_message TEXT,
                        timestamp DATETIME
                    )
                ''')
                
                # Create coverage metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coverage_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company TEXT,
                        total_articles INTEGER,
                        successful_scrapes INTEGER,
                        successful_summaries INTEGER,
                        date DATE
                    )
                ''')
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")

    def record_scraping_metrics(self, metrics: ScrapingMetrics):
        """Record scraping operation metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scraping_metrics 
                    (company, url, status, latency, content_length, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.company,
                    metrics.url,
                    metrics.status,
                    metrics.latency,
                    metrics.content_length,
                    metrics.error_message,
                    metrics.timestamp
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording scraping metrics: {str(e)}")

    def record_summary_metrics(self, metrics: SummaryMetrics):
        """Record summary generation metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO summary_metrics 
                    (company, url, latency, confidence_score, needs_review, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.company,
                    metrics.url,
                    metrics.latency,
                    metrics.confidence_score,
                    metrics.needs_review,
                    metrics.error_message,
                    metrics.timestamp
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording summary metrics: {str(e)}")

    def update_coverage_metrics(self, company: str, total: int, scraped: int, summarized: int):
        """Update coverage metrics for a company."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO coverage_metrics 
                    (company, total_articles, successful_scrapes, successful_summaries, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    company,
                    total,
                    scraped,
                    summarized,
                    datetime.now().date()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating coverage metrics: {str(e)}")

    def get_metrics_report(self) -> Dict[str, Any]:
        """Generate a comprehensive metrics report."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get scraping success rate
                scraping_df = pd.read_sql_query(
                    "SELECT company, status, COUNT(*) as count FROM scraping_metrics GROUP BY company, status",
                    conn
                )
                
                # Get summary confidence scores
                summary_df = pd.read_sql_query(
                    "SELECT company, AVG(confidence_score) as avg_confidence, COUNT(*) as total FROM summary_metrics GROUP BY company",
                    conn
                )
                  # Get coverage metrics
                coverage_df = pd.read_sql_query(
                    "SELECT company, AVG(successful_scrapes * 100.0 / total_articles) as scrape_coverage, "
                    "AVG(successful_summaries * 100.0 / total_articles) as summary_coverage "
                    "FROM coverage_metrics GROUP BY company",
                    conn
                )
                
                return {
                    'scraping_metrics': scraping_df.to_dict('records'),
                    'summary_metrics': summary_df.to_dict('records'),
                    'coverage_metrics': coverage_df.to_dict('records')                }
        except Exception as e:
            logger.error(f"Error generating metrics report: {str(e)}")
            return {}

    def get_low_confidence_summaries(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get summaries that need human review, excluding only obvious non-market-intelligence content."""
        import re
        from config import IRRELEVANT_URL_PATTERNS
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT company, url, confidence_score, timestamp
                    FROM summary_metrics
                    WHERE confidence_score < ? AND needs_review = 1
                    ORDER BY timestamp DESC
                ''', (threshold,))
                
                results = []
                for row in cursor.fetchall():
                    url = row[1]
                    confidence_score = row[2]
                      # Only skip URLs that are obviously irrelevant (privacy, legal, etc.)
                    # Be more selective - only filter out the most obvious non-market-intelligence content
                    highly_irrelevant_patterns = [
                        r'/privacy',
                        r'/legal/',
                        r'/cookies',
                        r'/terms',
                        r'cookiepedia\.co\.uk',
                        r'/modern-slavery-statement',
                        r'salesforce\.com/company/privacy',
                        r'/about$',
                        r'/contact$',
                        r'/careers$',
                        r'/jobs$',
                        r'/support/$'
                    ]
                    
                    is_highly_irrelevant = any(re.search(pattern, url, re.IGNORECASE) for pattern in highly_irrelevant_patterns)                    # Keep borderline summaries for review (0.4-0.7 range)
                    # Filter out very low confidence (< 0.4) and obvious irrelevant content
                    if confidence_score < 0.4:
                        continue
                    
                    # Skip if URL matches highly irrelevant patterns regardless of confidence
                    if is_highly_irrelevant:
                        continue
                    
                    results.append({
                        'company': row[0],
                        'url': url,
                        'confidence_score': confidence_score,
                        'timestamp': row[3]
                    })
                
                return results
        except Exception as e:
            logger.error(f"Error getting low confidence summaries: {str(e)}")
            return []

class QualityChecker:
    def __init__(self):
        """Initialize quality checker with thresholds."""
        self.min_confidence = 0.7  # Raised threshold to get more varied review candidates
        self.min_content_length = 100
        self.min_feature_count = 1
        
        # Product announcement keywords (strong indicators)
        self.product_keywords = [
            'announce', 'launch', 'release', 'introduce', 'unveil', 'preview',
            'new feature', 'enhancement', 'capability', 'integration', 'update',
            'available', 'generally available', 'public preview', 'beta'
        ]
        
        # Market intelligence indicators
        self.intelligence_keywords = [
            'partnership', 'acquisition', 'funding', 'investment', 'expansion',
            'customer', 'revenue', 'growth', 'market', 'competitive', 'strategy'
        ]
        
        # Technical depth indicators
        self.technical_keywords = [
            'api', 'sdk', 'integration', 'architecture', 'performance', 'scalability',
            'security', 'compliance', 'enterprise', 'cloud', 'ai', 'ml', 'data'
        ]

    def check_summary_quality(self, summary: Any) -> Dict[str, Any]:
        """Check quality of a summary with comprehensive scoring."""
        try:
            # Validate input type
            if not isinstance(summary, dict):
                logger.warning(f"Invalid summary type for quality check: expected dict, got {type(summary)}. Value: {summary}")
                return {
                    'confidence_score': 0.0,
                    'needs_review': True,
                    'reason': 'Invalid summary format',
                }
            
            # Initialize scoring components
            base_score = 0.5  # Start with neutral baseline
            content_score = 0.0
            relevance_score = 0.0
            depth_score = 0.0
            structure_score = 0.0
            
            reasons = []
            
            # 1. Content Quality Assessment (0-0.25 points)
            content = summary.get('content', '').lower()
            title = summary.get('title', '').lower()
            combined_text = f"{title} {content}"
            
            if len(content) > 200:
                content_score += 0.15
            elif len(content) > 100:
                content_score += 0.10
            elif len(content) > 50:
                content_score += 0.05
            else:
                reasons.append('Very short content')
            
            # Bonus for detailed content
            if len(content) > 500:
                content_score += 0.10
                
            # 2. Relevance Assessment (0-0.3 points)
            product_mentions = sum(1 for keyword in self.product_keywords if keyword in combined_text)
            intelligence_mentions = sum(1 for keyword in self.intelligence_keywords if keyword in combined_text)
            
            if product_mentions >= 3:
                relevance_score += 0.20
            elif product_mentions >= 2:
                relevance_score += 0.15
            elif product_mentions >= 1:
                relevance_score += 0.10
            else:
                reasons.append('Low product announcement indicators')
            
            if intelligence_mentions >= 2:
                relevance_score += 0.10
            elif intelligence_mentions >= 1:
                relevance_score += 0.05
                
            # 3. Technical Depth Assessment (0-0.15 points)
            technical_mentions = sum(1 for keyword in self.technical_keywords if keyword in combined_text)
            
            if technical_mentions >= 4:
                depth_score += 0.15
            elif technical_mentions >= 2:
                depth_score += 0.10
            elif technical_mentions >= 1:
                depth_score += 0.05
                
            # 4. Structure Quality Assessment (0-0.1 points)
            features = summary.get('features', [])
            if len(features) >= 3:
                structure_score += 0.10
            elif len(features) >= 2:
                structure_score += 0.07
            elif len(features) >= 1:
                structure_score += 0.05
            else:
                reasons.append('No specific features identified')
                # Add default feature if none found
                summary['features'] = ['No specific features identified']
            
            # Calculate final confidence score
            confidence_score = base_score + content_score + relevance_score + depth_score + structure_score
            
            # Apply penalties for obvious non-market-intelligence content
            url = summary.get('url', '').lower()
            if any(term in url for term in ['privacy', 'legal', 'about', 'contact', 'support']):
                confidence_score *= 0.3
                reasons.append('Non-market-intelligence URL pattern')
            elif any(term in combined_text for term in ['privacy policy', 'terms of service', 'cookie policy']):
                confidence_score *= 0.2
                reasons.append('Non-market-intelligence content')
            
            # Ensure score is within bounds
            confidence_score = max(0.0, min(1.0, confidence_score))
              # Handle social media section
            social_metrics = summary.get('social_metrics', {})
            total_mentions = sum(social_metrics.get(platform, 0) for platform in ['twitter', 'reddit', 'linkedin'])
            if total_mentions == 0 and 'social_metrics' in summary:
                del summary['social_metrics']
            
            # Determine if review is needed
            needs_review = confidence_score < self.min_confidence
            
            return {
                'confidence_score': confidence_score,
                'needs_review': needs_review,
                'reason': '; '.join(reasons) if reasons else None,
                'score_breakdown': {
                    'base': base_score,
                    'content': content_score,
                    'relevance': relevance_score,
                    'depth': depth_score,
                    'structure': structure_score
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking summary quality: {str(e)}")
            return {
                'confidence_score': 0.0,
                'needs_review': True,
                'reason': f'Error during quality check: {str(e)}'
            }