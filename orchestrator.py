"""
Agent orchestrator for the Market Intelligence Agent.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from scraper import AnnouncementScraper
from analyzer import AnnouncementAnalyzer
from formatter import SummaryFormatter
from monitoring import MetricsCollector, QualityChecker, ScrapingMetrics, SummaryMetrics
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    latency: float = 0.0

class AgentOrchestrator:
    def __init__(self):
        """Initialize the orchestrator with components."""
        self.scraper = AnnouncementScraper()
        self.analyzer = AnnouncementAnalyzer()
        self.formatter = SummaryFormatter()
        self.metrics = MetricsCollector()
        self.quality_checker = QualityChecker()

    def _execute_task(self, task_name: str, func, *args, **kwargs) -> TaskResult:
        """Execute a task with timing and error handling."""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return TaskResult(
                success=True,
                data=result,
                latency=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Error in {task_name}: {str(e)}")
            return TaskResult(
                success=False,
                data=None,
                error=str(e),
                latency=time.time() - start_time
            )

    def _record_scraping_metrics(self, company: str, url: str, result: TaskResult):
        """Record scraping operation metrics."""
        metrics = ScrapingMetrics(
            company=company,
            url=url,
            status='success' if result.success else 'error',
            latency=result.latency,
            content_length=len(result.data) if result.success and result.data else 0,
            error_message=result.error
        )
        self.metrics.record_scraping_metrics(metrics)

    def _record_summary_metrics(self, company: str, url: str, result: TaskResult):
        """Record summary generation metrics."""
        quality_check = self.quality_checker.check_summary_quality(result.data)
        metrics = SummaryMetrics(
            company=company,
            url=url,
            latency=result.latency,
            confidence_score=quality_check['confidence_score'],
            needs_review=quality_check['needs_review'],
            error_message=result.error
        )
        self.metrics.record_summary_metrics(metrics)

    def _validate_announcement(self, announcement: Any) -> bool:
        """Validate announcement object structure."""
        if not isinstance(announcement, dict):
            logger.warning(f"Skipping invalid announcement (not a dict): {announcement}")
            return False
        if 'text' not in announcement or not announcement['text']:
            logger.warning(f"Skipping announcement missing 'text' field: {announcement}")
            return False
        required_fields = ['title', 'text', 'date', 'url']
        missing_fields = [field for field in required_fields if field not in announcement]
        if missing_fields:
            logger.warning(f"Skipping announcement with missing fields {missing_fields}: {announcement.get('url', 'unknown URL')}")
            return False
        return True

    def process_company(self, company: str) -> List[Dict[str, Any]]:
        """Process announcements for a single company."""
        try:
            # Scrape announcements
            scraping_result = self._execute_task(
                'scraping',
                self.scraper.scrape_company,
                company
            )
            if not scraping_result.success:
                logger.error(f"Failed to scrape {company}: {scraping_result.error}")
                return []
            announcements = scraping_result.data
            if not announcements:
                logger.warning(f"No announcements found for {company}")
                return []
            processed_announcements = []
            for announcement in announcements:
                try:
                    # Enhanced validation
                    if not self._validate_announcement(announcement):
                        continue
                    # Analyze announcement
                    analysis_result = self._execute_task(
                        'analysis',
                        self.analyzer.analyze_announcement,
                        announcement
                    )
                    if not analysis_result.success:
                        logger.error(f"Failed to analyze announcement: {analysis_result.error}")
                        continue
                    # Format summary
                    summary_result = self._execute_task(
                        'formatting',
                        self.formatter.format_summary,
                        analysis_result.data
                    )
                    if not summary_result.success:
                        logger.error(f"Failed to format summary: {summary_result.error}")
                        continue
                    # Check for error/empty summaries
                    summary_text = analysis_result.data.get('summary', '').strip().lower()
                    if summary_text in [
                        'error generating summary. please review the original content.',
                        'no content available for summary.',
                        '',
                        None
                    ]:
                        logger.warning(f"Skipping useless summary for {announcement.get('url', 'unknown URL')}")
                        continue
                    # Record metrics
                    self._record_scraping_metrics(company, announcement['url'], scraping_result)
                    self._record_summary_metrics(company, announcement['url'], summary_result)
                    # Save summary
                    if summary_result.success:
                        self.formatter.save_summary(company, analysis_result.data)
                        processed_announcements.append(analysis_result.data)
                except Exception as e:
                    logger.error(f"Error processing announcement {announcement.get('url', 'unknown URL')}: {str(e)}")
                    continue
            # Update coverage metrics
            self.metrics.update_coverage_metrics(
                company=company,
                total=len(announcements),
                scraped=len(announcements),
                summarized=len(processed_announcements)
            )
            return processed_announcements
        except Exception as e:
            logger.error(f"Error processing company {company}: {str(e)}")
            return []

    def process_all_companies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Process announcements for all companies."""
        results = {}
        for company in self.scraper.watchlist['companies']:
            logger.info(f"Processing company: {company}")
            announcements = self.process_company(company)
            if announcements:
                results[company] = announcements
        
        return results

    def get_quality_report(self) -> Dict[str, Any]:
        """Generate a quality report."""
        try:
            # Get metrics report
            metrics_report = self.metrics.get_metrics_report()
            
            # Get low confidence summaries
            low_confidence = self.metrics.get_low_confidence_summaries()
            
            return {
                'metrics': metrics_report,
                'low_confidence_summaries': low_confidence,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating quality report: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate a coverage report."""
        try:
            with self.metrics.db_path as conn:
                # Get coverage metrics
                coverage_df = pd.read_sql_query('''
                    SELECT 
                        company,
                        AVG(successful_scrapes * 100.0 / total_articles) as scrape_coverage,
                        AVG(successful_summaries * 100.0 / total_articles) as summary_coverage,
                        COUNT(*) as days_processed
                    FROM coverage_metrics
                    GROUP BY company
                ''', conn)
                
                return {
                    'coverage': coverage_df.to_dict('records'),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error generating coverage report: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            } 