from scraper import HTTPFetcher, AnnouncementScraper
from bs4 import BeautifulSoup
import logging
logging.basicConfig(level=logging.INFO)

fetcher = HTTPFetcher()
scraper = AnnouncementScraper()

print('Testing date extraction from MCP article...')
content = fetcher.fetch('https://www.snowflake.com/en/blog/mcp-servers-unify-extend-data-agents/')
if content:
    print('Content fetched successfully')
    
    # Test date extraction
    date = scraper._extract_date_from_content(content, 'https://www.snowflake.com/en/blog/mcp-servers-unify-extend-data-agents/')
    print(f'Extracted date: {date}')
    
    # Look for date indicators in the content
    soup = BeautifulSoup(content, 'html.parser')
    
    # Look for time elements
    time_elements = soup.find_all(['time'])
    print(f'Found {len(time_elements)} time elements:')
    for time_elem in time_elements:
        datetime_attr = time_elem.get('datetime', '')
        text_content = time_elem.get_text(strip=True)
        print(f'  - datetime="{datetime_attr}", text="{text_content}"')
    
    # Look for date-related text
    text_content = soup.get_text()
    if 'JUL 15, 2025' in text_content:
        print('Found JUL 15, 2025 in text content!')
    elif 'July 15' in text_content:
        print('Found July 15 in text content!')
    else:
        print('Date text not found in obvious format')
        # Look for any 2025 mentions
        if '2025' in text_content:
            print('Found 2025 in content')
        else:
            print('No 2025 found in content')
else:
    print('Failed to fetch content')
