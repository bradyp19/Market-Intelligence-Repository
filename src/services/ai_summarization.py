#!/usr/bin/env python3
"""
AI Summarization Service for Competitive Intelligence
Integrates with OpenAI GPT-4 to generate intelligent summaries of competitor content.
"""

import os
import openai
from typing import Optional, Dict, Any
import logging
from datetime import datetime

class AISummarizationService:
    """Service for AI-powered content summarization and analysis."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        self.max_summary_length = int(os.getenv('MAX_SUMMARY_LENGTH', 500))
        self.logger = logging.getLogger(__name__)
    
    def summarize_content(self, title: str, content: str, competitor_name: str) -> Dict[str, Any]:
        """
        Generate an intelligent summary and analysis of competitor content.
        
        Args:
            title: Article title
            content: Full article content
            competitor_name: Name of the competitor
            
        Returns:
            Dict containing summary, category, priority, and confidence score
        """
        try:
            prompt = self._build_summarization_prompt(title, content, competitor_name)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a competitive intelligence analyst expert in data analytics, business intelligence, and enterprise software."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result = self._parse_ai_response(response.choices[0].message.content)
            
            self.logger.info(f"Generated AI summary for {competitor_name}: {title[:50]}...")
            return result
            
        except Exception as e:
            self.logger.error(f"AI summarization failed: {e}")
            return self._fallback_summary(title, content, competitor_name)
    
    def _build_summarization_prompt(self, title: str, content: str, competitor_name: str) -> str:
        """Build the prompt for AI summarization."""
        
        # Truncate content if too long
        if len(content) > 8000:
            content = content[:8000] + "..."
        
        return f"""
        Analyze this content from competitor "{competitor_name}" and provide a structured response:

        TITLE: {title}
        CONTENT: {content}

        Please provide your analysis in this EXACT format:

        SUMMARY: [Write a {self.max_summary_length}-character executive summary focusing on business impact and strategic implications]

        CATEGORY: [Choose ONE: product_launch, partnership, strategy, acquisition, funding, other]

        PRIORITY: [Choose ONE: high, medium, low - based on potential competitive threat or market impact]

        CONFIDENCE: [Number 0-100 indicating your confidence in the relevance and accuracy]

        KEY_INSIGHTS: [3-5 bullet points of strategic insights for our competitive intelligence team]

        TAGS: [3-5 relevant tags separated by commas, e.g., "cloud-analytics,partnership,enterprise"]

        Focus on:
        - Business impact and strategic implications
        - Competitive threats or opportunities
        - Technology trends and market positioning
        - Partnership and ecosystem developments
        """
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured AI response into a dictionary."""
        
        result = {
            'ai_summary': '',
            'relevance_category': 'other',
            'strategic_priority': 'medium',
            'confidence_score': 75.0,
            'key_insights': [],
            'tags': []
        }
        
        try:
            lines = response_text.strip().split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('SUMMARY:'):
                    result['ai_summary'] = line.replace('SUMMARY:', '').strip()[:self.max_summary_length]
                elif line.startswith('CATEGORY:'):
                    category = line.replace('CATEGORY:', '').strip().lower()
                    if category in ['product_launch', 'partnership', 'strategy', 'acquisition', 'funding', 'other']:
                        result['relevance_category'] = category
                elif line.startswith('PRIORITY:'):
                    priority = line.replace('PRIORITY:', '').strip().lower()
                    if priority in ['high', 'medium', 'low']:
                        result['strategic_priority'] = priority
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.replace('CONFIDENCE:', '').strip())
                        result['confidence_score'] = max(0, min(100, confidence))
                    except ValueError:
                        pass
                elif line.startswith('KEY_INSIGHTS:'):
                    current_section = 'insights'
                elif line.startswith('TAGS:'):
                    tags_text = line.replace('TAGS:', '').strip()
                    result['tags'] = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                elif current_section == 'insights' and line.startswith('- '):
                    result['key_insights'].append(line[2:].strip())
            
        except Exception as e:
            self.logger.error(f"Error parsing AI response: {e}")
        
        return result
    
    def _fallback_summary(self, title: str, content: str, competitor_name: str) -> Dict[str, Any]:
        """Provide a fallback summary when AI fails."""
        
        # Simple extractive summary - first 500 characters
        simple_summary = content[:self.max_summary_length] if content else title
        
        return {
            'ai_summary': f"[Auto-generated] {simple_summary}",
            'relevance_category': 'other',
            'strategic_priority': 'medium',
            'confidence_score': 50.0,
            'key_insights': [f"Content from {competitor_name} requires manual review"],
            'tags': ['auto-generated', 'needs-review']
        }

def integrate_ai_summarization():
    """
    Integration function to be called from the main scraper workflow.
    This should be added to your existing scraping pipeline.
    """
    
    # Example integration with your existing raw_fetch_queue processing
    from app_postgres import app, db, RawFetchQueue
    
    ai_service = AISummarizationService()
    
    with app.app_context():
        # Get pending items that need AI analysis
        pending_items = RawFetchQueue.query.filter(
            RawFetchQueue.status == 'pending',
            RawFetchQueue.ai_summary == None
        ).limit(10).all()
        
        for item in pending_items:
            try:
                # Generate AI summary
                ai_result = ai_service.summarize_content(
                    title=item.title or '',
                    content=item.content or '',
                    competitor_name=item.competitor.name
                )
                
                # Update the item with AI insights
                item.ai_summary = ai_result['ai_summary']
                item.relevance_category = ai_result['relevance_category']
                item.strategic_priority = ai_result['strategic_priority']
                item.confidence_score = ai_result['confidence_score']
                
                # Store additional insights in meta_info
                item.meta_info = {
                    **item.meta_info,
                    'ai_insights': ai_result['key_insights'],
                    'ai_tags': ai_result['tags'],
                    'ai_processed_at': datetime.utcnow().isoformat()
                }
                
                db.session.commit()
                
                print(f"✅ AI analysis completed for: {item.title[:50]}...")
                
            except Exception as e:
                print(f"❌ AI analysis failed for item {item.id}: {e}")
                continue

if __name__ == "__main__":
    # Test the AI service
    service = AISummarizationService()
    
    test_result = service.summarize_content(
        title="Snowflake Announces New Data Sharing Partnership",
        content="Snowflake has announced a strategic partnership with a major cloud provider to enhance data sharing capabilities across multiple regions...",
        competitor_name="Snowflake"
    )
    
    print("Test AI Summary Result:")
    for key, value in test_result.items():
        print(f"{key}: {value}")
