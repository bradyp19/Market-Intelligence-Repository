"""
Scraping module for the Market Intelligence Agent.
"""

import os
import json
import logging
import requests
import urllib3
import warnings
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from newspaper import Article
from urllib.parse import urljoin, urlparse
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from posixpath import normpath

# Disable SSL warnings for environments with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# Also disable all SSL-related warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

from config import (    COMPANY_SOURCES, PRODUCT_KEYWORDS, MAX_ARTICLES_PER_COMPANY,
    JS_HEAVY_DOMAINS, URL_FILTER_PATTERNS, IRRELEVANT_URL_PATTERNS, MIN_PUBLISH_DATE, MAX_PUBLISH_DATE,
    LOG_DIR
)

# Pre-compile regex patterns for performance
SOCIAL_MEDIA_DOMAINS = {
    'linkedin.com', 'facebook.com', 'twitter.com', 'x.com',
    'instagram.com', 'tiktok.com', 'youtube.com', 'reddit.com'
}

HIGHLY_IRRELEVANT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r'/privacy', r'/legal/', r'/cookies', r'/terms',
        r'cookiepedia\.co\.uk', r'/modern-slavery-statement',
        r'salesforce\.com/company/privacy',
        r'/careers', r'/jobs', r'/company/.*linkedin',
        r'/profile/', r'/people/', r'/in/'
    ]
]

CONTENT_PAGE_FILTERS = {
    '/tag/', '/category/', '/author/', '/search/', '/page/', 
    'privacy', 'legal', 'terms', 'cookies', '/profile/', '/people/', '/company/',
    '/tags', '/categories', '/authors', '/archive', '/archives'  # Added more filters
}

SOCIAL_PROFILE_FILTERS = {'/profile/', '/people/', '/company/', '/careers'}

# Additional URL patterns that should be excluded (navigation/utility pages)
NAVIGATION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r'/tags/?$',           # /tags or /tags/ (tag index pages)
        r'/tag/[^/]+/?$',      # /tag/something/ (individual tag pages)
        r'/categories/?$',     # Category index pages  
        r'/category/[^/]+/?$', # /category/something/ (individual category pages)
        r'/archive/?$',        # Archive index pages
        r'/archives/?$',       # Archive index pages (plural)
        r'/sitemap',           # Sitemap pages
        r'/rss',               # RSS feeds
        r'/feed',              # Feed pages
        r'/contact/?$',        # Contact pages
        r'/about/?$',          # About pages
        r'/subscribe/?$',      # Subscribe pages
        r'/newsletter/?$',     # Newsletter pages
        r'/unsubscribe',       # Unsubscribe pages
        r'\.xml$',             # XML files
        r'\.pdf$',             # PDF files (usually documents, not articles)
        r'/wp-admin',          # WordPress admin
        r'/wp-content',        # WordPress content directories
        r'/admin',             # Admin pages
        r'/login',             # Login pages
        r'/signup',            # Signup pages
        r'/register',          # Registration pages
        r'/author/[^/]+/?$',   # Author pages
        r'/search/?$',         # Search pages
        r'/page/\d+/?$',       # Pagination pages
    ]
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class URLValidator:
    """Handles URL validation and filtering logic."""
    
    def __init__(self, watchlist: Dict[str, Any]):
        self.watchlist = watchlist
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not excluded."""
        try:
            # Quick domain check for social media
            domain = urlparse(url).netloc.lower()
            if any(social_domain in domain for social_domain in SOCIAL_MEDIA_DOMAINS):
                return False
            
            # Check pre-compiled patterns (faster than checking raw patterns)
            if any(pattern.search(url) for pattern in HIGHLY_IRRELEVANT_PATTERNS):
                return False
                
            # Check navigation patterns (tag/category/admin pages)
            if any(pattern.search(url) for pattern in NAVIGATION_PATTERNS):
                return False
            
            # Check for excluded keywords
            if any(keyword in url.lower() for keyword in self.watchlist.get('excluded_keywords', [])):
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False
    
    def normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL efficiently using posixpath.normpath."""
        try:
            # Join with base URL if relative
            full_url = urljoin(base_url, url)
            
            # Parse URL
            parsed = urlparse(full_url)
            
            # Use posixpath.normpath for efficient path normalization
            clean_path = normpath(parsed.path) if parsed.path else '/'
            
            # Ensure leading slash
            if not clean_path.startswith('/'):
                clean_path = '/' + clean_path
                
            return f"{parsed.scheme}://{parsed.netloc}{clean_path}"
        except Exception as e:
            logger.error(f"Error normalizing URL {url}: {str(e)}")
            return urljoin(base_url, url)  # Fallback to simple join


class HTTPFetcher:
    """Handles HTTP requests with retry logic and error handling."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False  # SSL bypass for non-production
        
        # Track failures
        self.failed_urls = []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, 
                                     requests.exceptions.ConnectionError,
                                     requests.exceptions.HTTPError))
    )
    def _fetch_with_retry(self, url: str) -> Tuple[str, str]:
        """Fetch with retry logic for transient failures. Returns (content, final_url)."""
        response = self.session.get(url, timeout=45)
        response.raise_for_status()
        return response.text, response.url
    
    def fetch(self, url: str) -> Optional[str]:
        """Fetch page content with comprehensive error handling and redirect detection."""
        try:
            content, final_url = self._fetch_with_retry(url)
            
            # Check for problematic redirects (e.g., /tags -> homepage)
            if self._is_problematic_redirect(url, final_url):
                logger.warning(f"Detected problematic redirect: {url} -> {final_url}")
                self.failed_urls.append({
                    'url': url,
                    'error': f"Redirected to homepage/root: {final_url}",
                    'timestamp': datetime.now().isoformat()
                })
                return None
                
            return content
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [404, 403, 401]:
                logger.warning(f"Client error {e.response.status_code} for {url}")
                self.failed_urls.append({
                    'url': url,
                    'error': f"HTTP {e.response.status_code}",
                    'timestamp': datetime.now().isoformat()
                })
                return None
            else:
                logger.error(f"Server error {e.response.status_code} for {url}")
                raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.error(f"Network error for {url}: {str(e)}")
            self.failed_urls.append({
                'url': url,
                'error': f"Network error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {str(e)}")
            self.failed_urls.append({
                'url': url,
                'error': f"Unexpected: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })
            return None
    
    def _is_problematic_redirect(self, original_url: str, final_url: str) -> bool:
        """Check if this is a problematic redirect (e.g., tag pages to homepage)."""
        if original_url == final_url:
            return False  # No redirect occurred
            
        try:
            orig_parsed = urlparse(original_url)
            final_parsed = urlparse(final_url)
            
            # Same domain check
            if orig_parsed.netloc != final_parsed.netloc:
                return False  # Cross-domain redirect, probably legitimate
            
            # Check if final URL is homepage/root
            final_path = final_parsed.path.strip('/')
            if not final_path or final_path in ['', 'index.html', 'index.php', 'home']:
                # Original URL should not be homepage-ish
                orig_path = orig_parsed.path.strip('/')
                if orig_path and orig_path not in ['', 'index.html', 'index.php', 'home']:
                    return True  # Redirect from content page to homepage
            
            # Check for other problematic redirects (tag/category pages to listing pages)
            orig_path_lower = orig_parsed.path.lower()
            final_path_lower = final_parsed.path.lower()
            
            # If original has specific path but final is much shorter/generic
            if (len(orig_path_lower) > 10 and len(final_path_lower) < 5 and
                any(keyword in orig_path_lower for keyword in ['/tag', '/category', '/author'])):
                return True
                
            return False
        except Exception:
            return False  # If parsing fails, assume it's not problematic


class ContentExtractor:
    """Handles content extraction from HTML."""
    
    def __init__(self):
        self.parsing_failures = []
        
        # Pre-define content selectors for better performance
        self.content_selectors = [
            '.blog-post-content', '.post-body', '.entry-content', '.post-content-body',
            '.article-content', '.content-body', '.blog-content', '.post-text',
            'article .content', 'article', '.post-content', '.blog-content',
            'main article', 'main .content', '[role="main"]', '.main-content',
            '.content-area', '.entry', '.post', '.article-body',
            'main', '.content', '#content', '.container .content'
        ]
        
        self.title_selectors = ['h1', '.title', '.post-title', '.entry-title', '.article-title', '.blog-title']
        
        # Pre-compile junk patterns
        self.junk_patterns = [
            'cookie policy', 'privacy policy', 'terms of service', 'subscribe to newsletter',
            'follow us on', 'share this article', 'related articles', 'you might also like'
        ]
        
        # Boilerplate detection patterns (more comprehensive)
        self.boilerplate_patterns = [
            # Copyright and legal
            r'©\s*\d{4}.*?(all rights reserved|inc\.|corp\.|ltd\.)',
            r'copyright\s*\d{4}',
            r'all rights reserved',
            r'terms of use',
            r'privacy policy',
            
            # Navigation and UI
            r'click here to',
            r'subscribe to our newsletter',
            r'follow us on',
            r'share this article',
            r'back to top',
            r'next article',
            r'previous article',
            r'related posts',
            
            # Footer content
            r'contact us',
            r'about us',
            r'careers',
            r'press releases',
            r'investor relations',
            
            # Cookie and tracking
            r'we use cookies',
            r'accept cookies',
            r'cookie preferences',
            r'gdpr compliance'
        ]
        
        # Compile boilerplate patterns for performance
        self.compiled_boilerplate = [re.compile(pattern, re.IGNORECASE) for pattern in self.boilerplate_patterns]
    
    def extract_from_newspaper(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract using newspaper3k."""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            if article.text and len(article.text.strip()) >= 200:
                return {
                    'title': article.title,
                    'text': article.text,
                    'date': article.publish_date
                }
        except Exception as e:
            logger.warning(f"Newspaper3k failed for {url}: {str(e)}")
        return None
    
    def extract_manually(self, content: str, url: str) -> Optional[Dict[str, str]]:
        """Extract content manually using BeautifulSoup with quality assessment."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.select('script, style, nav, footer, header, aside, .sidebar, .navigation, .cookie, .privacy'):
                element.decompose()
            
            best_text = ""
            best_assessment = None
            
            # Try each selector and assess quality
            for selector in self.content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Clean element
                    for unwanted in element.select('.nav, .navigation, .sidebar, .menu, .header, .footer, .share, .social, .related-posts, .tags, .metadata'):
                        unwanted.decompose()
                    
                    text = element.get_text(separator=' ', strip=True)
                    
                    # Skip if obviously too short
                    if len(text) < 30:  # Lowered threshold
                        continue
                    
                    # Assess quality
                    assessment = self._assess_content_quality(element, text)
                    
                    # Keep if it's better quality
                    if (not best_assessment or 
                        assessment['quality_score'] > best_assessment['quality_score']):
                        best_text = text
                        best_assessment = assessment
            
            # Fallback: aggressive extraction if no good content found
            if not best_assessment or best_assessment['quality_score'] < 20:  # Lower bar
                logger.info(f"Trying aggressive extraction for {url}")
                for element in soup.select('.nav, .navigation, .sidebar, .menu, .footer, .header, .comments, .related, .share, .social, .metadata, .tags, .breadcrumb'):
                    element.decompose()
                
                body = soup.find('body')
                if body:
                    aggressive_text = body.get_text(separator=' ', strip=True)
                    aggressive_assessment = self._assess_content_quality(body, aggressive_text)
                    
                    # Use aggressive if it's better or if we have nothing
                    if (not best_assessment or 
                        aggressive_assessment['quality_score'] > best_assessment['quality_score']):
                        best_text = aggressive_text
                        best_assessment = aggressive_assessment
            
            # Store assessment for confidence scoring
            self.last_assessment = best_assessment
            
            # Validate content quality (now very forgiving)
            if not best_assessment or not self._is_content_valid(best_assessment, best_text):
                logger.warning(f"Content failed quality check for {url}: score={best_assessment['quality_score'] if best_assessment else 0}")
                return None
                
            # Clean text
            clean_text = self._clean_text(best_text)
            
            # Extract title
            title = self._extract_title(soup)
            
            logger.info(f"Extracted content from {url}: score={best_assessment['quality_score']}, chars={len(clean_text)}")
            return {'text': clean_text, 'title': title}
            
        except Exception as e:
            logger.error(f"Manual extraction failed for {url}: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text and remove boilerplate."""
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk and len(chunk) > 5)
        
        # Remove junk patterns
        for pattern in self.junk_patterns:
            clean_text = clean_text.replace(pattern, ' ')
        
        # Remove boilerplate using regex patterns
        for pattern in self.compiled_boilerplate:
            clean_text = pattern.sub(' ', clean_text)
        
        return ' '.join(clean_text.split())
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title from soup."""
        for title_selector in self.title_selectors:
            title_elem = soup.select_one(title_selector)
            if title_elem:
                return title_elem.get_text(strip=True)
        return None
    
    def _assess_content_quality(self, soup: BeautifulSoup, text: str) -> Dict[str, Any]:
        """Assess content quality using multiple signals beyond just character count."""
        assessment = {
            'char_count': len(text),
            'word_count': len(text.split()),
            'paragraph_count': 0,
            'heading_count': 0,
            'image_count': 0,
            'has_recent_date': False,
            'quality_score': 0
        }
        
        # Count structural elements
        assessment['paragraph_count'] = len(soup.find_all('p'))
        assessment['heading_count'] = len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        assessment['image_count'] = len(soup.find_all('img'))
        
        # Look for recent dates
        time_elements = soup.find_all(['time', '[datetime]', '.date', '.published', '.timestamp'])
        current_year = datetime.now().year
        
        for time_elem in time_elements:
            # Check datetime attribute
            dt_attr = time_elem.get('datetime', '')
            if str(current_year) in dt_attr or str(current_year - 1) in dt_attr:
                assessment['has_recent_date'] = True
                break
            
            # Check text content for years
            time_text = time_elem.get_text()
            if str(current_year) in time_text or str(current_year - 1) in time_text:
                assessment['has_recent_date'] = True
                break
        
        # Calculate quality score
        score = 0
        
        # Character count (more nuanced scoring)
        if assessment['char_count'] >= 500:
            score += 30
        elif assessment['char_count'] >= 200:
            score += 20
        elif assessment['char_count'] >= 100:
            score += 10
        
        # Word count
        if assessment['word_count'] >= 100:
            score += 20
        elif assessment['word_count'] >= 50:
            score += 10
        
        # Structural elements indicate real content
        if assessment['paragraph_count'] >= 3:
            score += 15
        elif assessment['paragraph_count'] >= 1:
            score += 5
        
        if assessment['heading_count'] >= 2:
            score += 10
        elif assessment['heading_count'] >= 1:
            score += 5
        
        # Images suggest rich content
        if assessment['image_count'] >= 1:
            score += 5
        
        # Recent dates suggest current content
        if assessment['has_recent_date']:
            score += 10
        
        # Check for announcement-style content patterns
        text_lower = text.lower()
        announcement_phrases = [
            'we are excited to announce', 'we are pleased to announce',
            'today we are launching', 'introducing', 'available now',
            'we are thrilled to', 'proud to announce'
        ]
        
        if any(phrase in text_lower for phrase in announcement_phrases):
            score += 15
        
        assessment['quality_score'] = min(score, 100)  # Cap at 100
        
        return assessment
    
    def _is_content_valid(self, assessment: Dict[str, Any], text: str) -> bool:
        """Very forgiving validation - capture everything, let confidence scoring decide quality."""
        # Minimum viable content thresholds (very low bar)
        min_chars = 30  # Very short snippets are still ok
        min_words = 5   # Even very brief announcements
        
        # Basic sanity checks only
        if assessment['char_count'] < min_chars or assessment['word_count'] < min_words:
            return False
        
        # Filter out pure navigation/boilerplate (only obvious cases)
        text_lower = text.lower().strip()
        
        # Reject if it's ONLY boilerplate
        pure_boilerplate = [
            'all rights reserved', 'copyright', 'terms of use', 'privacy policy',
            'click here', 'subscribe', 'follow us', 'contact us', 'about us'
        ]
        
        # If text is very short and consists mainly of boilerplate, reject
        if (assessment['char_count'] < 100 and 
            len([bp for bp in pure_boilerplate if bp in text_lower]) >= 2):
            return False
        
        # Otherwise, accept everything and let confidence scoring decide
        return True


class AnnouncementClassifier:
    """Classifies content as announcements or not."""
    
    def __init__(self, watchlist: Dict[str, Any]):
        self.watchlist = watchlist
        
        # Pre-define announcement indicators for performance
        self.announcement_indicators = [
            # Traditional announcement words
            'announcing', 'announced', 'introduces', 'launched', 'launches',
            'release', 'releasing', 'unveil', 'unveiling', 'debut', 'debuting',
            'preview', 'public preview', 'beta', 'general availability', 'ga',
            'new feature', 'new product', 'new service', 'new capability',
            'available now', 'now available',
            
            # Company-specific / Product launches
            'partnership', 'collaboration', 'integration',
            'acquisition', 'merger', 'spin-off', 'spin off',
            'certified', 'compliance', 'regulatory approval',
            'pre-order', 'pre order', 'now shipping', 'available for purchase',
            'upgrade', 'next-gen', 'next gen', 'v2', 'enhancement',
            
            # Global / Industry themes  
            'earnings', 'quarterly results', 'revenue', 'profit', 'growth',
            'funding', 'raise', 'ipo', 'valuation',
            'ai', 'machine learning', 'generative ai', 'gpt-4', 'data cloud',
            'sustainability', 'green', 'carbon footprint', 'net zero',
            
            # Communication & Education
            'webinar', 'deep dive', 'white paper', 'case study',
            'training', 'bootcamp', 'certification', 'workshop',
            'conference', 'panel', 'talk', 'keynote'
        ]
    
    def is_announcement(self, text: str, company: str) -> bool:
        """Check if content is likely an announcement."""
        try:
            company_keywords = self.watchlist['companies'].get(company, {}).get('keywords', [])
            global_keywords = self.watchlist.get('global_keywords', [])
            
            text_lower = text.lower()
            
            # Check announcement indicators
            for indicator in self.announcement_indicators:
                if indicator in text_lower:
                    logger.info(f"✅ Found announcement indicator '{indicator}' - marking as announcement")
                    return True
            
            # Check company and global keywords
            for keyword in company_keywords + global_keywords:
                if keyword.lower() in text_lower:
                    logger.info(f"✅ Found keyword '{keyword}' - marking as announcement")
                    return True
            
            logger.info(f"❌ No announcement keywords found in text: {text_lower[:100]}...")
            return False
            
        except Exception as e:
            logger.error(f"Error checking announcement: {str(e)}")
            return False


class ConfidenceScorer:
    """Calculates confidence scores for articles to rank them by quality and relevance."""
    
    def __init__(self, watchlist: Dict[str, Any]):
        self.watchlist = watchlist
        
        # Define scoring weights for different factors
        self.weights = {
            'content_quality': 0.3,      # 30% - How well-structured and substantial is the content
            'announcement_strength': 0.25, # 25% - How strong are the announcement indicators
            'company_relevance': 0.2,    # 20% - How relevant to the company's domain
            'recency': 0.15,            # 15% - How recent is the content
            'source_authority': 0.1     # 10% - Authority of the source/URL structure
        }
    
    def calculate_confidence(self, article: Dict[str, Any], company: str, assessment: Dict[str, Any] = None) -> float:
        """Calculate overall confidence score (0-100) for an article."""
        try:
            text = article.get('text', '')
            title = article.get('title', '')
            url = article.get('url', '')
            date = article.get('date')
            
            # Calculate individual scores
            content_score = self._score_content_quality(text, title, assessment)
            announcement_score = self._score_announcement_strength(text, title, company)
            relevance_score = self._score_company_relevance(text, title, company)
            recency_score = self._score_recency(date)
            authority_score = self._score_source_authority(url)
            
            # Calculate weighted total
            confidence = (
                content_score * self.weights['content_quality'] +
                announcement_score * self.weights['announcement_strength'] +
                relevance_score * self.weights['company_relevance'] +
                recency_score * self.weights['recency'] +
                authority_score * self.weights['source_authority']
            )
            
            # Log detailed scoring for transparency
            logger.info(f"Confidence scoring for {url[:50]}...")
            logger.info(f"  Content: {content_score:.1f}, Announcement: {announcement_score:.1f}, "
                       f"Relevance: {relevance_score:.1f}, Recency: {recency_score:.1f}, "
                       f"Authority: {authority_score:.1f} -> Total: {confidence:.1f}")
            
            return min(confidence, 100.0)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.0
    
    def _score_content_quality(self, text: str, title: str, assessment: Dict[str, Any] = None) -> float:
        """Score content quality (0-100)."""
        if not text:
            return 0.0
        
        score = 0.0
        
        # Use existing assessment if available
        if assessment:
            # Leverage the quality assessment we already calculated
            base_score = assessment.get('quality_score', 0)
            score += base_score * 0.6  # 60% from existing assessment
            
            # Additional quality indicators
            if assessment.get('paragraph_count', 0) >= 3:
                score += 15
            if assessment.get('heading_count', 0) >= 2:
                score += 10
            if assessment.get('has_recent_date', False):
                score += 10
        else:
            # Fallback scoring if no assessment
            char_count = len(text)
            word_count = len(text.split())
            
            # Length scoring
            if char_count >= 1000:
                score += 40
            elif char_count >= 500:
                score += 30
            elif char_count >= 200:
                score += 20
            elif char_count >= 100:
                score += 10
            
            # Word density and readability
            if word_count >= 150:
                score += 20
            elif word_count >= 75:
                score += 15
            elif word_count >= 30:
                score += 10
        
        # Title quality
        if title and len(title) > 10:
            score += 10
            # Professional title indicators
            title_lower = title.lower()
            if any(word in title_lower for word in ['announces', 'launches', 'introduces', 'releases']):
                score += 5
        
        # Content structure indicators
        text_lower = text.lower()
        
        # Professional language patterns
        professional_indicators = [
            'we are pleased to announce', 'we are excited to', 'today we',
            'this release', 'our customers', 'our platform', 'our solution'
        ]
        score += min(sum(5 for phrase in professional_indicators if phrase in text_lower), 15)
        
        # Technical depth indicators
        technical_terms = [
            'api', 'integration', 'platform', 'architecture', 'framework',
            'machine learning', 'artificial intelligence', 'cloud', 'data'
        ]
        score += min(sum(2 for term in technical_terms if term in text_lower), 10)
        
        return min(score, 100.0)
    
    def _score_announcement_strength(self, text: str, title: str, _company: str) -> float:
        """Score how strong the announcement indicators are (0-100)."""
        score = 0.0
        combined_text = f"{title} {text}".lower()
        
        # Strong announcement verbs
        strong_verbs = [
            'announcing', 'announces', 'launched', 'launches', 'introduces', 
            'unveiling', 'unveils', 'releasing', 'debuts'
        ]
        score += min(sum(15 for verb in strong_verbs if verb in combined_text), 45)
        
        # Medium strength indicators
        medium_indicators = [
            'available now', 'now available', 'general availability', 'public preview',
            'partnership', 'collaboration', 'acquisition', 'integration'
        ]
        score += min(sum(10 for indicator in medium_indicators if indicator in combined_text), 30)
        
        # Business event indicators
        business_events = [
            'earnings', 'quarterly results', 'funding', 'ipo', 'revenue',
            'growth', 'expansion', 'investment'
        ]
        score += min(sum(8 for event in business_events if event in combined_text), 24)
        
        # Product/feature announcements
        product_terms = [
            'new feature', 'new product', 'enhancement', 'upgrade', 'v2',
            'next generation', 'improved', 'faster', 'better'
        ]
        score += min(sum(5 for term in product_terms if term in combined_text), 20)
        
        # Press/media style language
        press_language = [
            'press release', 'for immediate release', 'media contact',
            'conference', 'keynote', 'presentation'
        ]
        score += min(sum(8 for phrase in press_language if phrase in combined_text), 16)
        
        return min(score, 100.0)
    
    def _score_company_relevance(self, text: str, title: str, company: str) -> float:
        """Score relevance to the specific company and its domain (0-100)."""
        score = 0.0
        combined_text = f"{title} {text}".lower()
        
        # Company name mentions
        company_lower = company.lower()
        if company_lower in combined_text:
            # Count mentions but with diminishing returns
            mentions = combined_text.count(company_lower)
            score += min(mentions * 10, 30)
        
        # Company-specific keywords from watchlist
        company_config = self.watchlist['companies'].get(company, {})
        company_keywords = company_config.get('keywords', [])
        
        for keyword in company_keywords:
            if keyword.lower() in combined_text:
                score += 8
        
        # Industry/domain relevance
        domain_terms = {
            'Snowflake': ['data warehouse', 'data lake', 'analytics', 'sql', 'cloud'],
            'Databricks': ['spark', 'machine learning', 'lakehouse', 'delta', 'mlflow'],
            'Tableau': ['visualization', 'dashboard', 'charts', 'analytics'],
            'Power BI': ['business intelligence', 'microsoft', 'analytics', 'reporting'],
            'Domo': ['business intelligence', 'dashboard', 'kpi', 'metrics']
        }
        
        relevant_terms = domain_terms.get(company, [])
        for term in relevant_terms:
            if term in combined_text:
                score += 5
        
        # Global industry keywords
        global_keywords = self.watchlist.get('global_keywords', [])
        for keyword in global_keywords:
            if keyword.lower() in combined_text:
                score += 3
        
        return min(score, 100.0)
    
    def _score_recency(self, date) -> float:
        """Score based on how recent the content is (0-100)."""
        if not date:
            return 50.0  # Neutral score if no date
        
        try:
            if isinstance(date, str):
                # Try to parse string dates
                from dateutil import parser
                date = parser.parse(date)
            
            if not hasattr(date, 'year'):
                return 50.0
            
            current_date = datetime.now()
            days_old = (current_date - date).days
            
            # Scoring based on age
            if days_old <= 1:
                return 100.0  # Published today or yesterday
            elif days_old <= 7:
                return 90.0   # This week
            elif days_old <= 30:
                return 80.0   # This month
            elif days_old <= 90:
                return 70.0   # Last 3 months
            elif days_old <= 180:
                return 60.0   # Last 6 months
            elif days_old <= 365:
                return 50.0   # This year
            else:
                # Older content gets lower scores
                years_old = days_old / 365.0
                return max(20.0, 50.0 - (years_old * 10))
                
        except Exception as e:
            logger.warning(f"Error scoring recency: {str(e)}")
            return 50.0
    
    def _score_source_authority(self, url: str) -> float:
        """Score based on URL structure and source authority (0-100)."""
        if not url:
            return 50.0
        
        score = 50.0  # Start with neutral
        url_lower = url.lower()
        
        # Official company blog/news sections get higher scores
        if '/blog/' in url_lower:
            score += 20
        elif '/news/' in url_lower:
            score += 25
        elif '/press-release' in url_lower or '/press/' in url_lower:
            score += 30
        
        # Structured URLs (with dates, categories) often indicate quality
        if re.search(r'/\d{4}/', url):  # Year in URL
            score += 10
        if re.search(r'/\d{4}/\d{2}/', url):  # Year/month in URL
            score += 5
        
        # Clean URL structure (no query params, reasonable length)
        if '?' not in url and len(url) < 150:
            score += 10
        
        # Penalty for very deep URLs (might be auto-generated)
        url_depth = url.count('/') - 2  # Subtract protocol and domain
        if url_depth > 6:
            score -= 10
        
        # Penalty for URLs with suspicious patterns
        suspicious_patterns = ['temp', 'test', 'draft', 'staging', 'dev.']
        if any(pattern in url_lower for pattern in suspicious_patterns):
            score -= 20
        
        return max(min(score, 100.0), 0.0)

class AnnouncementScraper:
    """Main scraper that orchestrates URL validation, fetching, and content extraction."""
    
    def __init__(self, watchlist_path: str = 'watchlist.json'):
        """Initialize the scraper with separated components."""
        self.watchlist = self._load_watchlist(watchlist_path)
        
        # Initialize components
        self.url_validator = URLValidator(self.watchlist)
        self.fetcher = HTTPFetcher()
        self.extractor = ContentExtractor()
        self.classifier = AnnouncementClassifier(self.watchlist)
        self.confidence_scorer = ConfidenceScorer(self.watchlist)
        
        # Configuration for confidence-based filtering
        self.min_confidence_threshold = 30.0  # Very forgiving threshold
        self.max_articles_per_company = 5
        self.scorer = ConfidenceScorer(self.watchlist)

    def _load_watchlist(self, path: str) -> Dict[str, Any]:
        """Load watchlist configuration from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading watchlist: {str(e)}")
            return {"companies": {}, "global_keywords": [], "excluded_keywords": []}

    def _is_url_potentially_recent(self, url: str) -> bool:
        """Quick check if URL might contain recent content based on URL patterns."""
        try:
            # Extract year patterns from URL
            year_matches = re.findall(r'/(\d{4})/', url)
            
            # If we find years in the URL, check if any are recent
            if year_matches:
                years = [int(year) for year in year_matches if year.isdigit()]
                if years:
                    # If all years found are before 2024, skip this URL
                    max_year = max(years)
                    if max_year < 2024:
                        logger.debug(f"Skipping URL with old year {max_year}: {url[:60]}...")
                        return False
            
            # Check for obvious old date patterns in URL path and query params
            url_lower = url.lower()
            old_patterns = [
                r'/2023/', r'/2022/', r'/2021/', r'/2020/', r'/2019/', r'/2018/',
                r'/202[0-3]/', r'/201\d/',  # Broader patterns for 2010s-2023
                r'year=202[0-3]', r'year=201\d',  # Query parameters
                r'date=202[0-3]', r'date=201\d',  # Date query parameters
            ]
            
            for pattern in old_patterns:
                if re.search(pattern, url):
                    logger.debug(f"Skipping URL with old date pattern '{pattern}': {url[:60]}...")
                    return False
            
            # Also check for month/year patterns like /2023/01/ or /2022/12/
            if re.search(r'/202[0-3]/\d{2}/', url):
                logger.debug(f"Skipping URL with old month/year pattern: {url[:60]}...")
                return False
                    
            return True  # URL seems potentially recent or undetermined
            
        except Exception as e:
            logger.warning(f"Error checking URL date patterns for {url}: {str(e)}")
            return True  # If unsure, allow processing

    def _extract_links(self, content: str, base_url: str) -> List[str]:
        """Extract and validate links from page content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            links = []
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                    continue
                
                # Convert relative URLs to absolute
                normalized_url = self.url_validator.normalize_url(href, base_url)
                
                # Skip URLs that are obviously too old (performance optimization)
                if not self._is_url_potentially_recent(normalized_url):
                    continue
                
                # Skip social media links entirely
                domain = urlparse(normalized_url).netloc.lower()
                if any(social in domain for social in SOCIAL_MEDIA_DOMAINS):
                    continue
                
                # Filter blog/news content
                if self._is_content_url(normalized_url):
                    links.append(normalized_url)
                elif self.url_validator.is_valid_url(normalized_url):
                    if not any(pattern in normalized_url.lower() for pattern in SOCIAL_PROFILE_FILTERS):
                        links.append(normalized_url)
            
            return list(set(links))  # Remove duplicates
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            return []
    
    def _is_content_url(self, url: str) -> bool:
        """Check if URL looks like a blog/news content page."""
        return (
            ('/blog/' in url or '/news/' in url or '/press-release' in url) and
            not any(pattern in url.lower() for pattern in CONTENT_PAGE_FILTERS)
        )

    def _extract_date_from_content(self, content: str, url: str) -> Optional[datetime]:
        """Try to extract publication date from page content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Common date selectors
            date_selectors = [
                'time[datetime]',
                '.published-date',
                '.publish-date',
                '.date-published',
                '.post-date',
                '.article-date',
                '[class*="date"]',
                '[class*="published"]',
                '.blog-meta',           # Common blog metadata areas
                '.post-meta',           # Post metadata
                '.article-meta',        # Article metadata
                '.entry-meta'           # Entry metadata
            ]
            
            for selector in date_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Try datetime attribute first
                    if element.name == 'time' and element.get('datetime'):
                        try:
                            from dateutil import parser
                            return parser.parse(element['datetime']).replace(tzinfo=None)
                        except:
                            continue
                    
                    # Try text content
                    text = element.get_text(strip=True)
                    if text and len(text) > 6:  # Minimum date length
                        try:
                            from dateutil import parser
                            # Handle common blog date formats like "JUL 15, 2025 | 4 MIN READ"
                            # Extract just the date part before any pipe or extra content
                            date_text = text.split('|')[0].strip()
                            date_text = text.split('•')[0].strip()  # Handle bullet separators too
                            
                            parsed_date = parser.parse(date_text, fuzzy=True)
                            # Only accept dates that seem reasonable (not too far in future)
                            if parsed_date.year >= 2020 and parsed_date.year <= 2030:
                                return parsed_date.replace(tzinfo=None)
                        except Exception:
                            continue
            
            # Try meta tags
            meta_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="date"]',
                'meta[name="pubdate"]',
                'meta[name="publish-date"]'
            ]
            
            for selector in meta_selectors:
                element = soup.select_one(selector)
                if element and element.get('content'):
                    try:
                        from dateutil import parser
                        return parser.parse(element['content']).replace(tzinfo=None)
                    except:
                        continue
                        
        except Exception as e:
            logger.warning(f"Date extraction failed for {url}: {str(e)}")
        
        return None

    def _is_within_date_range(self, article_date: Optional[datetime]) -> bool:
        """Check if article date is within the specified range (July 4-15, 2025)."""
        if not article_date:
            # If no date is available, keep the article (assume it's recent)
            # This prevents missing important announcements due to date extraction failures
            logger.info("No date found - keeping article (assuming recent)")
            return True
        
        # Ensure article_date is timezone-naive for comparison
        if article_date.tzinfo is not None:
            article_date = article_date.replace(tzinfo=None)
        
        return MIN_PUBLISH_DATE <= article_date <= MAX_PUBLISH_DATE

    def _extract_article_content(self, url: str, company: str) -> Optional[Dict[str, Any]]:
        """Extract article content and calculate confidence score."""
        try:
            # Try newspaper3k first
            result = self.extractor.extract_from_newspaper(url)
            assessment = None
            
            # If that fails, try manual extraction
            if not result:
                content = self.fetcher.fetch(url)
                if content:
                    manual_result = self.extractor.extract_manually(content, url)
                    if manual_result:
                        # Try to extract date from the page content
                        article_date = self._extract_date_from_content(content, url)
                        result = {
                            'title': manual_result.get('title'),
                            'text': manual_result.get('text'),
                            'date': article_date  # Use extracted date or None
                        }
                        # Get the assessment for confidence scoring
                        if hasattr(self.extractor, 'last_assessment'):
                            assessment = self.extractor.last_assessment
            
            if not result or not result.get('text'):
                return None
            
            # Create article object with proper date handling
            extracted_date = result['date']
            article = {
                'title': result['title'] or self._extract_title_from_url(url),
                'text': result['text'],
                'date': extracted_date,  # Keep original date, don't default to now()
                'url': url
            }
            
            # Check date filtering first - reject if outside date range
            if not self._is_within_date_range(article['date']):
                logger.info(f"Article rejected due to date filter: {url[:50]}... "
                           f"(date: {article['date'].strftime('%Y-%m-%d') if article['date'] else 'None'})")
                return None
            
            # Calculate confidence score
            confidence = self.confidence_scorer.calculate_confidence(article, company, assessment)
            article['confidence_score'] = confidence
            
            # Log for transparency
            logger.info(f"Article processed: {url[:50]}... | Confidence: {confidence:.1f} | Length: {len(article['text'])}")
            
            return article
            
        except Exception as e:
            logger.error(f"Unexpected error extracting article content from {url}: {str(e)}")
            self.extractor.parsing_failures.append({
                'url': url,
                'error': f"Unexpected error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })
            return None

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from URL if other methods fail."""
        try:
            path = urlparse(url).path
            title_part = path.split('/')[-2] if path.endswith('/') else path.split('/')[-1]
            return title_part.replace('-', ' ').replace('_', ' ').title()
        except Exception:
            return "Article"

    def scrape_company(self, company: str) -> List[Dict[str, Any]]:
        """Scrape all articles for a company and return the highest confidence ones."""
        try:
            if company not in self.watchlist['companies']:
                logger.error(f"Company {company} not found in watchlist")
                return []
            
            company_config = self.watchlist['companies'][company]
            processed_urls = set()
            all_articles = []
            
            # Process both blog and press URLs - collect ALL articles
            for url_type in ['blog_url', 'press_url']:
                if url_type not in company_config:
                    continue
                    
                articles = self._process_url_source_confidence_based(company_config[url_type], company, processed_urls)
                all_articles.extend(articles)
            
            # Filter by minimum confidence threshold
            qualified_articles = [
                article for article in all_articles 
                if article.get('confidence_score', 0) >= self.min_confidence_threshold
            ]
            
            # Sort by confidence score (highest first)
            qualified_articles.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
            
            # Take top articles
            top_articles = qualified_articles[:self.max_articles_per_company]
            
            # Log confidence summary
            if qualified_articles:
                avg_confidence = sum(a.get('confidence_score', 0) for a in qualified_articles) / len(qualified_articles)
                logger.info(f"{company}: Found {len(qualified_articles)} qualified articles "
                           f"(avg confidence: {avg_confidence:.1f}), returning top {len(top_articles)}")
                
                # Log top articles
                for i, article in enumerate(top_articles, 1):
                    confidence = article.get('confidence_score', 0)
                    title = article.get('title', 'No title')[:50]
                    logger.info(f"  {i}. {title}... (confidence: {confidence:.1f})")
            else:
                logger.warning(f"{company}: No articles met minimum confidence threshold of {self.min_confidence_threshold}")
            
            return top_articles
            
        except Exception as e:
            logger.error(f"Error scraping company {company}: {str(e)}")
            return []
    
    def _process_url_source_confidence_based(self, base_url: str, company: str, processed_urls: set) -> List[Dict[str, Any]]:
        """Process a URL source and return all articles with confidence scores."""
        all_articles = []
        
        content = self.fetcher.fetch(base_url)
        if not content:
            return all_articles
        
        links = self._extract_links(content, base_url)
        logger.info(f"Processing {len(links)} links for {company} from {base_url}")
        
        processed_count = 0
        skipped_count = 0
        
        for link in links:
            if link in processed_urls:
                continue
                
            processed_urls.add(link)
            
            # Additional URL-based filtering before processing
            if not self._is_url_potentially_recent(link):
                skipped_count += 1
                continue
                
            article = self._extract_article_content(link, company)
            if article:
                # Add all articles regardless of traditional announcement classification
                # Confidence scoring will handle quality ranking
                all_articles.append(article)
                processed_count += 1
        
        logger.info(f"Processed {processed_count} articles, skipped {skipped_count} old URLs for {company}")
        return all_articles

    def _process_url_source(self, base_url: str, company: str, processed_urls: set, all_articles: list) -> List[Dict[str, Any]]:
        """Process a single URL source (blog or press)."""
        announcements = []
        
        content = self.fetcher.fetch(base_url)
        if not content:
            return announcements
        
        links = self._extract_links(content, base_url)
        for link in links:
            if link in processed_urls:
                continue
                
            processed_urls.add(link)
            article = self._extract_article_content(link, company)
            if article:
                if self.classifier.is_announcement(article['text'], company):
                    announcements.append(article)
                else:
                    all_articles.append(article)
        
        return announcements

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
        
        # Save failure reports
        self.save_failure_reports()
        
        # Log summary
        total_failed = len(self.fetcher.failed_urls)
        total_parsing_failed = len(self.extractor.parsing_failures)
        if total_failed or total_parsing_failed:
            logger.warning(f"Completed with {total_failed} failed URLs and {total_parsing_failed} parsing failures")
        
        return results

    def save_failure_reports(self) -> None:
        """Save failed URLs and parsing failures for manual inspection."""
        try:
            os.makedirs('logs', exist_ok=True)
            
            if self.fetcher.failed_urls:
                failed_urls_path = os.path.join('logs', 'failed_urls.json')
                with open(failed_urls_path, 'w', encoding='utf-8') as f:
                    json.dump(self.fetcher.failed_urls, f, indent=2)
                logger.info(f"Saved {len(self.fetcher.failed_urls)} failed URLs to {failed_urls_path}")
            
            if self.extractor.parsing_failures:
                parsing_failures_path = os.path.join('logs', 'parsing_failures.json')
                with open(parsing_failures_path, 'w', encoding='utf-8') as f:
                    json.dump(self.extractor.parsing_failures, f, indent=2)
                logger.info(f"Saved {len(self.extractor.parsing_failures)} parsing failures to {parsing_failures_path}")
                
        except Exception as e:
            logger.error(f"Error saving failure reports: {str(e)}")

    def get_failure_summary(self) -> Dict[str, Any]:
        """Get a summary of failures for reporting."""
        return {
            'failed_urls_count': len(self.fetcher.failed_urls),
            'parsing_failures_count': len(self.extractor.parsing_failures),
            'failed_urls': self.fetcher.failed_urls,
            'parsing_failures': self.extractor.parsing_failures
        }