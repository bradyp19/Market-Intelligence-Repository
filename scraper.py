"""
Scraping module for the Market Intelligence Agent.
"""

import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from newspaper import Article
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
import re

from config import (
    COMPANY_SOURCES, PRODUCT_KEYWORDS, MAX_ARTICLES_PER_COMPANY,
    JS_HEAVY_DOMAINS, URL_FILTER_PATTERNS, MIN_PUBLISH_DATE,
    LOG_DIR
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnnouncementScraper:
    def __init__(self, watchlist_path: str = 'watchlist.json'):
        """Initialize the scraper with watchlist configuration."""
        self.watchlist = self._load_watchlist(watchlist_path)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _load_watchlist(self, path: str) -> Dict[str, Any]:
        """Load watchlist configuration from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading watchlist: {str(e)}")
            return {"companies": {}, "global_keywords": [], "excluded_keywords": []}

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not excluded."""
        try:
            # Check for excluded patterns
            excluded_patterns = [
                r'/blog/blog/',
                r'/company/newsroom/company/newsroom/',
                r'/tags/',
                r'/categories/',
                r'/roles/',
                r'\?Type_equal=',
                r'\?utm_source=',
                r'\?utm_medium=',
                r'\?utm_campaign=',
                r'/author/',
                r'/page/',
                r'/about/',
                r'/contact/',
                r'/demo/',
                r'/pricing/',
                r'/solutions/'
            ]
            
            if any(re.search(pattern, url) for pattern in excluded_patterns):
                return False
            
            # Check for excluded keywords
            if any(keyword in url.lower() for keyword in self.watchlist['excluded_keywords']):
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False

    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL by removing duplicates and cleaning up."""
        try:
            # Join with base URL if relative
            full_url = urljoin(base_url, url)
            
            # Parse URL
            parsed = urlparse(full_url)
            
            # Remove duplicate path segments
            path_parts = parsed.path.split('/')
            unique_parts = []
            for part in path_parts:
                if part and part not in unique_parts:
                    unique_parts.append(part)
            
            # Reconstruct URL
            clean_path = '/' + '/'.join(unique_parts)
            return f"{parsed.scheme}://{parsed.netloc}{clean_path}"
        except Exception as e:
            logger.error(f"Error normalizing URL {url}: {str(e)}")
            return url

    def _get_page_content(self, url: str) -> Optional[str]:
        """Get page content using appropriate method based on domain."""
        try:
            domain = urlparse(url).netloc
            
            # Use Playwright for JavaScript-heavy sites
            if any(js_domain in domain for js_domain in [
                'snowflake.com',
                'tableau.com',
                'powerbi.microsoft.com'
            ]):
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page()
                    page.goto(url, wait_until='networkidle')
                    content = page.content()
                    browser.close()
                    return content
            
            # Use requests for other sites
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {str(e)}")
            return None

    def _extract_links(self, content: str, base_url: str) -> List[str]:
        """Extract and validate links from page content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            links = []
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                    continue
                
                normalized_url = self._normalize_url(href, base_url)
                if self._is_valid_url(normalized_url):
                    links.append(normalized_url)
            
            return list(set(links))  # Remove duplicates
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            return []

    def _is_announcement(self, text: str, company: str) -> bool:
        """Check if content is likely an announcement."""
        try:
            # Get company-specific keywords
            company_keywords = self.watchlist['companies'][company]['keywords']
            
            # Combine with global keywords
            all_keywords = company_keywords + self.watchlist['global_keywords']
            
            # Check for keywords in text
            text_lower = text.lower()
            return any(keyword.lower() in text_lower for keyword in all_keywords)
        except Exception as e:
            logger.error(f"Error checking announcement: {str(e)}")
            return False

    def _extract_article_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract article content using newspaper3k."""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            # Keep the 2025 date filter
            if article.publish_date and article.publish_date < datetime(2025, 1, 1):
                return None
            
            return {
                'title': article.title,
                'text': article.text,
                'date': article.publish_date or datetime.now(),
                'url': url
            }
        except Exception as e:
            logger.error(f"Error extracting article content from {url}: {str(e)}")
            return None

    def scrape_company(self, company: str) -> List[Dict[str, Any]]:
        """Scrape announcements for a specific company."""
        try:
            if company not in self.watchlist['companies']:
                logger.error(f"Company {company} not found in watchlist")
                return []
            
            company_config = self.watchlist['companies'][company]
            announcements = []
            processed_urls = set()
            all_articles = []  # Store all articles temporarily
            
            # Try both blog and press URLs
            for url_type in ['blog_url', 'press_url']:
                if url_type not in company_config:
                    continue
                    
                base_url = company_config[url_type]
                content = self._get_page_content(base_url)
                if not content:
                    continue
                
                links = self._extract_links(content, base_url)
                for link in links:
                    if link in processed_urls:
                        continue
                        
                    processed_urls.add(link)
                    article = self._extract_article_content(link)
                    if article:
                        if self._is_announcement(article['text'], company):
                            announcements.append(article)
                            if len(announcements) >= 5:  # Limit to 5 announcements per company
                                break
                        else:
                            # Store non-announcement articles as potential fallback
                            all_articles.append(article)
                
                if len(announcements) >= 5:  # If we found enough announcements, we can stop
                    break
            
            # Fallback: If no announcements found, use the most recent article from 2025
            if not announcements and all_articles:
                # Sort articles by date (most recent first) and take the first one
                sorted_articles = sorted(all_articles, key=lambda x: x['date'], reverse=True)
                if sorted_articles:
                    announcements.append(sorted_articles[0])
            
            return announcements
        except Exception as e:
            logger.error(f"Error scraping company {company}: {str(e)}")
            return []

    def scrape_all_companies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape announcements for all companies in watchlist."""
        results = {}
        for company in self.watchlist['companies']:
            logger.info(f"Scraping announcements for {company}")
            announcements = self.scrape_company(company)
            if announcements:
                results[company] = announcements
            else:
                logger.warning(f"No announcements found for {company}")
        return results 