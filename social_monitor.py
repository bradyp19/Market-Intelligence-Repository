"""
Social media and forum monitoring module for the Market Intelligence Agent.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tweepy
import praw
from linkedin_api import Linkedin
from stackapi import StackAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SocialMediaMonitor:
    def __init__(self):
        """Initialize social media API clients."""
        # Twitter/X API setup
        self.twitter_client = tweepy.Client(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        )
        
        # Reddit API setup
        self.reddit_client = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        # LinkedIn API setup
        self.linkedin_client = Linkedin(
            os.getenv('LINKEDIN_EMAIL'),
            os.getenv('LINKEDIN_PASSWORD')
        )
        
        # Stack Overflow API setup
        self.stack_client = StackAPI('stackoverflow')

    def get_twitter_mentions(self, company: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent Twitter mentions for a company."""
        try:
            # Search for tweets mentioning the company
            query = f"{company} (announcement OR launch OR release OR new feature)"
            tweets = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'public_metrics', 'entities']
            )
            
            results = []
            for tweet in tweets.data or []:
                results.append({
                    'platform': 'Twitter',
                    'content': tweet.text,
                    'date': tweet.created_at,
                    'url': f"https://twitter.com/user/status/{tweet.id}",
                    'engagement': tweet.public_metrics
                })
            return results
        except Exception as e:
            logger.error(f"Error fetching Twitter data for {company}: {str(e)}")
            return []

    def get_reddit_posts(self, company: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get relevant Reddit posts about a company."""
        try:
            subreddits = ['dataengineering', 'datascience', 'businessintelligence']
            results = []
            
            for subreddit in subreddits:
                posts = self.reddit_client.subreddit(subreddit).search(
                    f"{company} announcement",
                    time_filter='week',
                    limit=10
                )
                
                for post in posts:
                    results.append({
                        'platform': 'Reddit',
                        'content': post.title + "\n" + post.selftext,
                        'date': datetime.fromtimestamp(post.created_utc),
                        'url': f"https://reddit.com{post.permalink}",
                        'subreddit': subreddit,
                        'score': post.score
                    })
            return results
        except Exception as e:
            logger.error(f"Error fetching Reddit data for {company}: {str(e)}")
            return []

    def get_linkedin_posts(self, company: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get relevant LinkedIn posts about a company."""
        try:
            # Search for company posts
            search_results = self.linkedin_client.search_posts(
                keywords=f"{company} announcement",
                time_posted='past_week'
            )
            
            results = []
            for post in search_results:
                results.append({
                    'platform': 'LinkedIn',
                    'content': post.get('content', ''),
                    'date': datetime.fromtimestamp(post.get('created_time', 0)),
                    'url': post.get('url', ''),
                    'author': post.get('author', {}).get('name', '')
                })
            return results
        except Exception as e:
            logger.error(f"Error fetching LinkedIn data for {company}: {str(e)}")
            return []

    def get_stackoverflow_posts(self, company: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get relevant Stack Overflow posts about a company's products."""
        try:
            # Search for questions tagged with company's products
            questions = self.stack_client.fetch(
                'search/advanced',
                tagged=f"{company.lower()}",
                fromdate=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                sort='votes',
                order='desc'
            )
            
            results = []
            for question in questions.get('items', []):
                results.append({
                    'platform': 'Stack Overflow',
                    'content': question['title'] + "\n" + question.get('body', ''),
                    'date': datetime.fromtimestamp(question['creation_date']),
                    'url': question['link'],
                    'score': question['score'],
                    'tags': question['tags']
                })
            return results
        except Exception as e:
            logger.error(f"Error fetching Stack Overflow data for {company}: {str(e)}")
            return []

    def get_all_social_mentions(self, company: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get all social media mentions for a company."""
        all_mentions = []
        
        # Get mentions from each platform
        all_mentions.extend(self.get_twitter_mentions(company, days))
        all_mentions.extend(self.get_reddit_posts(company, days))
        all_mentions.extend(self.get_linkedin_posts(company, days))
        all_mentions.extend(self.get_stackoverflow_posts(company, days))
        
        # Sort by date
        all_mentions.sort(key=lambda x: x['date'], reverse=True)
        
        return all_mentions 