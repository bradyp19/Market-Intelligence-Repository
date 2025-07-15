#!/usr/bin/env python3
"""Quick test of Snowflake processing."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import AnnouncementScraper

def test_snowflake():
    """Test Snowflake article discovery."""
    scraper = AnnouncementScraper()
    
    print("Testing Snowflake article discovery...")
    print("=" * 50)
    
    # Test Snowflake company processing
    articles = scraper.scrape_company("Snowflake")
    
    print(f"\nFound {len(articles)} articles for Snowflake:")
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article.get('title', 'No title')[:60]}...")
        print(f"   URL: {article.get('url', 'No URL')}")
        print(f"   Confidence: {article.get('confidence_score', 0):.1f}")
        print(f"   Date: {article.get('date', 'No date')}")
        print()

if __name__ == "__main__":
    test_snowflake()
