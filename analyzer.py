"""
Analysis module for the Market Intelligence Agent.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
import re
import spacy

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnnouncementAnalyzer:
    def __init__(self):
        """Initialize analyzer with NLP components."""
        self.nlp = spacy.load('en_core_web_sm')
        self.feature_patterns = [
            r'new (?:feature|capability|functionality)',
            r'introduc(?:e|ing) (?:new|the)',
            r'launch(?:ed|ing) (?:new|the)',
            r'enhance(?:d|ment)',
            r'improve(?:d|ment)',
            r'add(?:ed|ing) (?:new|support for)',
            r'integrat(?:e|ed|ion)',
            r'partnership with',
            r'acquir(?:e|ed)'
        ]
        self.default_feature = "No specific features identified"
        self.stop_words = set(stopwords.words('english'))
        try:
            from social_monitor import SocialMediaMonitor
            self.social_monitor = SocialMediaMonitor()
            self.social_enabled = True
        except Exception as e:
            logger.warning(f"Social monitoring disabled: {e}")
            self.social_monitor = None
            self.social_enabled = False

    def _extract_features(self, text: str) -> List[str]:
        """Extract features with fallback mechanisms."""
        try:
            if not text:
                return [self.default_feature]
            
            # Try pattern matching first
            features = []
            for pattern in self.feature_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Get the sentence containing the match
                    start = max(0, text.rfind('.', 0, match.start()))
                    end = text.find('.', match.end())
                    if end == -1:
                        end = len(text)
                    sentence = text[start:end].strip()
                    if sentence and len(sentence) > 10:  # Avoid very short sentences
                        features.append(sentence)
            
            # If no features found, try NLP-based extraction
            if not features:
                doc = self.nlp(text)
                for sent in doc.sents:
                    # Look for sentences with product-related keywords
                    if any(keyword in sent.text.lower() for keyword in ['feature', 'capability', 'function', 'support']):
                        features.append(sent.text.strip())
            
            # If still no features, use fallback
            if not features:
                return [self.default_feature]
            
            # Clean and deduplicate features
            cleaned_features = []
            seen = set()
            for feature in features:
                # Clean the feature text
                cleaned = ' '.join(feature.split())
                if cleaned and cleaned not in seen and len(cleaned) > 10:
                    cleaned_features.append(cleaned)
                    seen.add(cleaned)
            
            return cleaned_features or [self.default_feature]
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return [self.default_feature]

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text using basic keyword matching."""
        try:
            # Simple sentiment analysis based on keyword matching
            positive_words = {'innovative', 'powerful', 'seamless', 'efficient', 'advanced',
                            'breakthrough', 'revolutionary', 'game-changing', 'cutting-edge'}
            negative_words = {'limited', 'complex', 'challenging', 'restricted', 'basic'}
            
            words = word_tokenize(text.lower())
            words = [w for w in words if w not in self.stop_words]
            
            positive_count = sum(1 for w in words if w in positive_words)
            negative_count = sum(1 for w in words if w in negative_words)
            total_count = len(words)
            
            if total_count == 0:
                return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
            
            positive_score = positive_count / total_count
            negative_score = negative_count / total_count
            neutral_score = 1 - (positive_score + negative_score)
            
            return {
                'positive': positive_score,
                'negative': negative_score,
                'neutral': neutral_score
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}

    def analyze_social_mentions(self, company: str, days: int = 7) -> Dict[str, Any]:
        """Analyze social media mentions for a company. Returns empty/default if social monitoring is disabled."""
        if not getattr(self, 'social_enabled', False) or not self.social_monitor:
            return {
                'total_mentions': 0,
                'platform_breakdown': {},
                'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0},
                'top_mentions': []
            }
        try:
            mentions = self.social_monitor.get_all_social_mentions(company, days)
            
            # Analyze sentiment and engagement
            analysis = {
                'total_mentions': len(mentions),
                'platform_breakdown': {},
                'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0},
                'top_mentions': []
            }
            
            for mention in mentions:
                # Update platform breakdown
                platform = mention['platform']
                analysis['platform_breakdown'][platform] = analysis['platform_breakdown'].get(platform, 0) + 1
                
                # Analyze sentiment
                sentiment = self.analyze_sentiment(mention['content'])
                max_sentiment = max(sentiment.items(), key=lambda x: x[1])[0]
                analysis['sentiment_breakdown'][max_sentiment] += 1
                
                # Track engagement metrics
                engagement = mention.get('engagement', {})
                if engagement:
                    mention['engagement_score'] = sum(engagement.values())
                else:
                    mention['engagement_score'] = mention.get('score', 0)
            
            # Sort mentions by engagement score
            mentions.sort(key=lambda x: x.get('engagement_score', 0), reverse=True)
            analysis['top_mentions'] = mentions[:5]
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing social mentions: {str(e)}")
            return {
                'total_mentions': 0,
                'platform_breakdown': {},
                'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0},
                'top_mentions': []
            }

    def analyze_announcement(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an announcement with improved error handling and fallback content."""
        try:
            if not isinstance(announcement, dict):
                logger.warning(f"Invalid announcement type: expected dict, got {type(announcement)}. Value: {announcement}")
                return {
                    'title': announcement.get('title', ''),
                    'date': announcement.get('date', None),
                    'url': announcement.get('url', ''),
                    'content': '',
                    'features': ['No specific features identified'],
                    'summary': 'No specific features identified.'
                }
            # Extract required fields with validation
            title = announcement.get('title', '')
            text = announcement.get('text', '')
            url = announcement.get('url', '')
            date = announcement.get('date')
            if not text:
                logger.warning(f"Announcement has no content: {url}")
                return {
                    'title': title,
                    'date': date,
                    'url': url,
                    'content': '',
                    'features': ['No specific features identified'],
                    'summary': 'No specific features identified.'
                }
            # Extract features with fallback
            features = self._extract_features(text)
            if not features or features == ['No specific features identified']:
                logger.warning(f"No features identified for announcement: {url}")
                features = ['No specific features identified']
                summary = 'No specific features identified.'
            else:
                summary = self._generate_summary(text, features)
            # Build analysis result (without social media metrics)
            result = {
                'title': title,
                'date': date,
                'url': url,
                'content': text,
                'features': features,
                'summary': summary
            }
            return result
        except Exception as e:
            logger.error(f"Error analyzing announcement for {announcement.get('url', 'unknown URL')}: {str(e)} | Raw: {announcement}")
            return {
                'title': announcement.get('title', ''),
                'date': announcement.get('date', None),
                'url': announcement.get('url', ''),
                'content': '',
                'features': ['No specific features identified'],
                'summary': 'No specific features identified.'
            }

    def _generate_summary(self, text: str, features: List[str]) -> str:
        """Generate a summary with fallback for missing content."""
        try:
            if not text:
                return "No content available for summary."
            
            # Generate summary using NLP
            doc = self.nlp(text)
            summary_sentences = []
            
            # Try to get the first few sentences that contain feature information
            for sent in doc.sents:
                if any(feature.lower() in sent.text.lower() for feature in features):
                    summary_sentences.append(sent.text)
                if len(summary_sentences) >= 3:
                    break
            
            # If no feature-related sentences found, use the first few sentences
            if not summary_sentences:
                summary_sentences = [sent.text for sent in list(doc.sents)[:3]]
            
            return ' '.join(summary_sentences)
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Error generating summary. Please review the original content." 