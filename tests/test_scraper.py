"""
Unit tests for the scraper module.
"""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from scraper import AnnouncementScraper
from monitoring import QualityChecker

class TestScraper(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = AnnouncementScraper()
        self.quality_checker = QualityChecker()

    def test_url_validation(self):
        """Test URL validation logic."""
        # Valid URLs
        valid_urls = [
            "https://www.snowflake.com/blog/2025/01/01/new-feature",
            "https://www.databricks.com/blog/2025/02/01/announcement",
            "https://www.domo.com/blog/2025/03/01/release"
        ]
        for url in valid_urls:
            self.assertTrue(self.scraper._is_valid_url(url))

        # Invalid URLs
        invalid_urls = [
            "https://www.snowflake.com/blog/blog/2025/01/01/new-feature",
            "https://www.databricks.com/company/newsroom/company/newsroom/2025/02/01/announcement",
            "https://www.domo.com/blog/tags/job",
            "https://www.snowflake.com/blog/author/john-doe",
            "https://www.databricks.com/blog?Type_equal=press"
        ]
        for url in invalid_urls:
            self.assertFalse(self.scraper._is_valid_url(url))

    def test_url_normalization(self):
        """Test URL normalization logic."""
        base_url = "https://www.snowflake.com/blog"
        test_cases = [
            (
                "/2025/01/01/new-feature",
                "https://www.snowflake.com/blog/2025/01/01/new-feature"
            ),
            (
                "https://www.snowflake.com/blog/2025/01/01/new-feature",
                "https://www.snowflake.com/blog/2025/01/01/new-feature"
            ),
            (
                "/blog/2025/01/01/new-feature",
                "https://www.snowflake.com/blog/2025/01/01/new-feature"
            )
        ]
        for input_url, expected_url in test_cases:
            normalized = self.scraper._normalize_url(input_url, base_url)
            self.assertEqual(normalized, expected_url)

    @patch('scraper.AnnouncementScraper._get_page_content')
    def test_content_quality_check(self, mock_get_content):
        """Test content quality checking."""
        # Mock successful content
        mock_get_content.return_value = """
        <html>
            <body>
                <h1>New Feature Announcement</h1>
                <p>We are excited to announce our new feature that enables...</p>
                <p>This enhancement provides...</p>
            </body>
        </html>
        """
        content = self.scraper._get_page_content("https://example.com")
        quality_check = self.quality_checker.check_scraping_quality(content, "https://example.com")
        self.assertTrue(quality_check['is_valid'])

        # Mock error page
        mock_get_content.return_value = """
        <html>
            <body>
                <h1>Error 404 - Page Not Found</h1>
            </body>
        </html>
        """
        content = self.scraper._get_page_content("https://example.com")
        quality_check = self.quality_checker.check_scraping_quality(content, "https://example.com")
        self.assertFalse(quality_check['is_valid'])

    def test_announcement_detection(self):
        """Test announcement detection logic."""
        # Valid announcement
        valid_text = """
        We are excited to announce our new feature that enables data sharing across organizations.
        This enhancement provides improved performance and security.
        """
        self.assertTrue(self.scraper._is_announcement(valid_text, "Snowflake"))

        # Invalid announcement
        invalid_text = """
        Join our upcoming webinar to learn about career opportunities.
        We are hiring for multiple positions.
        """
        self.assertFalse(self.scraper._is_announcement(invalid_text, "Snowflake"))

    def test_summary_quality_check(self):
        """Test summary quality checking."""
        # High quality summary
        good_summary = {
            'title': 'New Feature Announcement',
            'date': datetime.now(),
            'url': 'https://example.com',
            'features': [
                'Enhanced data sharing capabilities',
                'Improved performance metrics',
                'New security features'
            ],
            'sentiment': {
                'positive': 0.8,
                'negative': 0.1,
                'neutral': 0.1
            }
        }
        quality_check = self.quality_checker.check_summary_quality(good_summary)
        self.assertFalse(quality_check['needs_review'])
        self.assertGreater(quality_check['confidence_score'], 0.8)

        # Low quality summary
        bad_summary = {
            'title': 'New Feature',
            'date': datetime.now(),
            'url': 'https://example.com',
            'features': ['New feature'],
            'sentiment': {
                'positive': 0.3,
                'negative': 0.3,
                'neutral': 0.4
            }
        }
        quality_check = self.quality_checker.check_summary_quality(bad_summary)
        self.assertTrue(quality_check['needs_review'])
        self.assertLess(quality_check['confidence_score'], 0.7)

if __name__ == '__main__':
    unittest.main() 