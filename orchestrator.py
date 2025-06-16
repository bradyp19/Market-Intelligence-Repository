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
import os
import shutil

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

    def _is_market_intelligence(self, announcement: dict) -> bool:
        """Return True if the announcement is likely market intelligence, False if it's a legal/privacy/cookie/about/careers/etc page."""
        if not isinstance(announcement, dict):
            return False
        title = (announcement.get('title') or '').lower()
        url = (announcement.get('url') or '').lower()
        # Add more keywords as needed
        skip_keywords = [
            'privacy', 'cookie', 'legal', 'terms', 'about', 'careers', 'jobs', 'esg', 'who we are', 'overview',
            'policy', 'compliance', 'support', 'contact', 'faq', 'help', 'modern slavery', 'gdpr', 'accessibility',
            'press kit', 'customer support', 'site terms', 'consent', 'copyright', 'disclaimer', 'investor relations',
            'partners', 'leadership', 'team', 'board', 'governance', 'statement', 'giving-consent', 'sustainability',
            'diversity', 'inclusion', 'trust', 'security', 'responsibility', 'ethics', 'transparency', 'csr', 'csr-report',
            'community', 'donate', 'donation', 'foundation', 'philanthropy', 'volunteer', 'events', 'event', 'webinar',
            'training', 'academy', 'university', 'learning', 'education', 'blog/authors', 'blog/category', 'blog/tags',
            'blog/labels', 'blog/partners', 'blog/privacy', 'blog/legal', 'blog/about', 'blog/careers', 'blog/support',
            'blog/overview', 'blog/press', 'blog/contact', 'blog/faq', 'blog/help', 'blog/giving-consent', 'blog/statement',
            'blog/gdpr', 'blog/accessibility', 'blog/press-kit', 'blog/customer-support', 'blog/site-terms', 'blog/consent',
            'blog/copyright', 'blog/disclaimer', 'blog/investor-relations', 'blog/leadership', 'blog/team', 'blog/board',
            'blog/governance', 'blog/sustainability', 'blog/diversity', 'blog/inclusion', 'blog/trust', 'blog/security',
            'blog/responsibility', 'blog/ethics', 'blog/transparency', 'blog/csr', 'blog/csr-report', 'blog/community',
            'blog/donate', 'blog/donation', 'blog/foundation', 'blog/philanthropy', 'blog/volunteer', 'blog/events',
            'blog/event', 'blog/webinar', 'blog/training', 'blog/academy', 'blog/university', 'blog/learning', 'blog/education'
        ]
        for kw in skip_keywords:
            if kw in title or kw in url:
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
                    # Strict market intelligence filter
                    if not self._is_market_intelligence(announcement):
                        logger.info(f"Skipping non-market-intelligence announcement: {announcement.get('url', 'unknown URL')} | Title: {announcement.get('title', '')}")
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

    def run(self):
        """Main entry point for the agent."""
        # Delete all summaries at the start of each run
        summaries_root = 'summaries'
        if os.path.exists(summaries_root):
            shutil.rmtree(summaries_root)
        os.makedirs(summaries_root, exist_ok=True)
        # ... rest of run logic ...
        for company in self.scraper.watchlist['companies']:
            self.process_company(company)
        # After processing, keep only top 3 summaries per company
        self._keep_top_summaries(max_per_company=3)

    def _keep_top_summaries(self, max_per_company=3):
        import glob
        from dateutil.parser import parse
        summaries_root = 'summaries'
        if not os.path.exists(summaries_root):
            return
        for company in os.listdir(summaries_root):
            company_dir = os.path.join(summaries_root, company)
            if not os.path.isdir(company_dir):
                continue
            summary_files = glob.glob(os.path.join(company_dir, '*.md'))
            summary_infos = []
            for file in summary_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    confidence = 0.0
                    date = None
                    for line in content.splitlines():
                        if 'confidence:' in line.lower():
                            try:
                                confidence = float(line.split(':')[-1].strip())
                            except Exception:
                                confidence = 0.0
                        if line.lower().startswith('headline:') and '(' in line:
                            try:
                                date_str = line.split('(')[-1].split(')')[0].split(',')[-1].strip()
                                date = parse(date_str, fuzzy=True)
                            except Exception:
                                date = None
                    if not date:
                        date = datetime.fromtimestamp(os.path.getmtime(file))
                    summary_infos.append({
                        'file': file,
                        'confidence': confidence,
                        'date': date
                    })
                except Exception:
                    continue
            summary_infos.sort(key=lambda x: (x['confidence'], x['date']), reverse=True)
            to_keep = set(x['file'] for x in summary_infos[:max_per_company])
            for info in summary_infos[max_per_company:]:
                try:
                    os.remove(info['file'])
                except Exception:
                    pass 