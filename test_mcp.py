#!/usr/bin/env python3
"""Test script to verify the MCP article processing."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import AnnouncementScraper

def test_mcp_article():
    """Test the specific MCP article that should be captured."""
    scraper = AnnouncementScraper()
    
    # Test the specific MCP article
    mcp_url = "https://www.snowflake.com/en/blog/mcp-servers-unify-extend-data-agents/"
    
    print(f"Testing MCP article: {mcp_url}")
    print("=" * 60)
    
    # Test direct article extraction
    article = scraper._extract_article_content(mcp_url, "Snowflake")
    
    if article:
        print(f"✅ SUCCESS: Article processed!")
        print(f"Title: {article.get('title', 'No title')}")
        print(f"Date: {article.get('date', 'No date')}")
        print(f"Confidence: {article.get('confidence_score', 0):.1f}")
        print(f"Text length: {len(article.get('text', ''))}")
        print(f"Text preview: {article.get('text', '')[:200]}...")
    else:
        print("❌ FAILED: Article was not processed")

if __name__ == "__main__":
    test_mcp_article()
