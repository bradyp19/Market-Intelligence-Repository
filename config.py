"""
Configuration settings for the Market Intelligence Agent.
"""

from datetime import datetime

# Company blog and press release URLs
COMPANY_SOURCES = {
    'Snowflake': {
        'blog_url': 'https://www.snowflake.com/blog/',
        'press_url': 'https://www.snowflake.com/news-events/press-releases/'
    },
    'Databricks': {
        'blog_url': 'https://www.databricks.com/blog',
        'press_url': 'https://www.databricks.com/company/newsroom'
    },
    'Domo': {
        'blog_url': 'https://www.domo.com/blog',
        'press_url': 'https://www.domo.com/company/press-releases'
    },
    'Tableau': {
        'blog_url': 'https://www.tableau.com/blog',
        'press_url': 'https://www.tableau.com/about/press-releases'
    },
    'Power BI': {
        'blog_url': 'https://powerbi.microsoft.com/en-us/blog/',
        'press_url': 'https://news.microsoft.com/tag/power-bi/'
    },
    'Starburst': {
        'blog_url': 'https://www.starburst.io/blog/',
        'press_url': 'https://www.starburst.io/press-releases/'
    },
    'Denodo': {
        'blog_url': 'https://www.denodo.com/en/blog',
        'press_url': 'https://www.denodo.com/en/press-releases'
    },
    'ThoughtSpot': {
        'blog_url': 'https://www.thoughtspot.com/blog',
        'press_url': 'https://www.thoughtspot.com/company/press-releases'
    }
}

# Keywords to identify product announcements
PRODUCT_KEYWORDS = [
    'announce', 'launch', 'release', 'introduce', 'new feature',
    'product update', 'enhancement', 'capability', 'integration',
    'unveil', 'preview', 'showcase', 'demonstrate'
]

# Maximum number of articles to process per company
MAX_ARTICLES_PER_COMPANY = 5

# Output settings
OUTPUT_DIR = 'summaries'
LOG_DIR = 'logs'

# Domains that require JavaScript rendering
JS_HEAVY_DOMAINS = [
    'snowflake.com',
    'tableau.com',
    'powerbi.microsoft.com'
]

# URL patterns to filter out
URL_FILTER_PATTERNS = [
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

# Minimum publish date (January 1, 2025)
MIN_PUBLISH_DATE = datetime(2025, 1, 1) 