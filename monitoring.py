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
                    'coverage_metrics': coverage_df.to_dict('records')
                }
        except Exception as e:
            logger.error(f"Error generating metrics report: {str(e)}")
            return {}

    def get_low_confidence_summaries(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get summaries that need human review."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT company, url, confidence_score, timestamp
                    FROM summary_metrics
                    WHERE confidence_score < ? AND needs_review = 1
                    ORDER BY timestamp DESC
                ''', (threshold,))
                
                return [
                    {
                        'company': row[0],
                        'url': row[1],
                        'confidence_score': row[2],
                        'timestamp': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting low confidence summaries: {str(e)}")
            return []

class QualityChecker:
    def __init__(self):
        """Initialize quality checker with thresholds."""
        self.min_confidence = 0.6
        self.min_content_length = 100
        self.min_feature_count = 1

    def check_summary_quality(self, summary: Any) -> Dict[str, Any]:
        """Check quality of a summary with graceful error handling."""
        try:
            # Validate input type
            if not isinstance(summary, dict):
                logger.warning(f"Invalid summary type for quality check: expected dict, got {type(summary)}. Value: {summary}")
                return {
                    'confidence_score': 0.0,
                    'needs_review': True,
                    'reason': 'Invalid summary format',
                }
            
            # Initialize quality metrics
            quality_score = 1.0
            reasons = []
            
            # Check content length
            content = summary.get('content', '')
            if not content or len(content) < self.min_content_length:
                quality_score *= 0.7
                reasons.append('Content too short or missing')
            
            # Check features
            features = summary.get('features', [])
            if not features or len(features) < self.min_feature_count:
                quality_score *= 0.8
                reasons.append('Insufficient features identified')
                # Add default feature if none found
                if not features:
                    summary['features'] = ['No specific features identified']
            
            # Check social media section
            social_metrics = summary.get('social_metrics', {})
            total_mentions = sum(social_metrics.get(platform, 0) for platform in ['twitter', 'reddit', 'linkedin'])
            if total_mentions == 0:
                # Remove social media section if no mentions
                if 'social_metrics' in summary:
                    del summary['social_metrics']
            
            # Determine if review is needed
            needs_review = quality_score < self.min_confidence
            
            return {
                'confidence_score': quality_score,
                'needs_review': needs_review,
                'reason': '; '.join(reasons) if reasons else None
            }
            
        except Exception as e:
            logger.error(f"Error checking summary quality: {str(e)}")
            return {
                'confidence_score': 0.0,
                'needs_review': True,
                'reason': f'Error during quality check: {str(e)}'
            } 