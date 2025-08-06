#!/usr/bin/env python3
"""
Alerting Service for Competitive Intelligence
Sends Slack and email notifications when high-priority updates are approved.
"""

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import requests
import logging
from datetime import datetime, timezone

class AlertingService:
    """Service for sending alerts about high-priority competitive updates."""
    
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.email_smtp_host = os.getenv('EMAIL_SMTP_HOST')
        self.email_smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        self.email_username = os.getenv('EMAIL_USERNAME')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_from = os.getenv('EMAIL_FROM')
        self.email_to = os.getenv('EMAIL_TO', '').split(',')
        self.logger = logging.getLogger(__name__)
    
    def send_high_priority_alert(self, update_data: Dict[str, Any]) -> bool:
        """
        Send alert for high-priority competitive updates.
        
        Args:
            update_data: Dictionary containing update information
            
        Returns:
            bool: True if at least one alert was sent successfully
        """
        success = False
        
        # Send Slack alert
        if self.slack_webhook:
            try:
                if self._send_slack_alert(update_data):
                    success = True
                    self.logger.info(f"Slack alert sent for: {update_data.get('title', 'Unknown')}")
            except Exception as e:
                self.logger.error(f"Failed to send Slack alert: {e}")
        
        # Send email alert
        if self.email_smtp_host and self.email_username:
            try:
                if self._send_email_alert(update_data):
                    success = True
                    self.logger.info(f"Email alert sent for: {update_data.get('title', 'Unknown')}")
            except Exception as e:
                self.logger.error(f"Failed to send email alert: {e}")
        
        return success
    
    def _send_slack_alert(self, update_data: Dict[str, Any]) -> bool:
        """Send Slack notification for high-priority update."""
        
        # Build Slack message
        competitor_name = update_data.get('competitor_name', 'Unknown')
        title = update_data.get('title', 'No title')
        summary = update_data.get('summary', 'No summary available')
        url = update_data.get('url', '')
        priority = update_data.get('strategic_priority', 'medium')
        category = update_data.get('relevance_category', 'other')
        confidence = update_data.get('confidence_score', 0)
        approved_by = update_data.get('approved_by', 'Unknown')
        
        # Create rich Slack message
        slack_payload = {
            "text": f"🚨 High Priority Competitive Update: {competitor_name}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 High Priority: {competitor_name}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Title:*\n{title}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Priority:* {priority.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Category:* {category.replace('_', ' ').title()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Confidence:* {confidence}%"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:*\n{summary[:500]}..."
                    }
                }
            ]
        }
        
        # Add URL button if available
        if url:
            slack_payload["blocks"].append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Original"
                        },
                        "url": url,
                        "style": "primary"
                    }
                ]
            })
        
        # Add footer with approval info
        slack_payload["blocks"].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Approved by {approved_by} • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                }
            ]
        })
        
        # Send to Slack
        response = requests.post(
            self.slack_webhook,
            json=slack_payload,
            timeout=10
        )
        
        return response.status_code == 200
    
    def _send_email_alert(self, update_data: Dict[str, Any]) -> bool:
        """Send email notification for high-priority update."""
        
        competitor_name = update_data.get('competitor_name', 'Unknown')
        title = update_data.get('title', 'No title')
        summary = update_data.get('summary', 'No summary available')
        url = update_data.get('url', '')
        priority = update_data.get('strategic_priority', 'medium')
        category = update_data.get('relevance_category', 'other')
        confidence = update_data.get('confidence_score', 0)
        approved_by = update_data.get('approved_by', 'Unknown')
        
        # Create email content
        subject = f"🚨 High Priority Competitive Update: {competitor_name} - {title[:50]}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;">
                    🚨 High Priority Competitive Update
                </h2>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">{competitor_name}</h3>
                    <h4 style="color: #34495e; margin-bottom: 15px;">{title}</h4>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold; width: 120px;">Priority:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #e74c3c;">{priority.upper()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Category:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{category.replace('_', ' ').title()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Confidence:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{confidence}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Approved by:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{approved_by}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: white; padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin: 20px 0;">
                    <h4 style="color: #2c3e50; margin-top: 0;">Summary:</h4>
                    <p style="color: #555; line-height: 1.8;">{summary}</p>
                </div>
                
                {"<p><a href='" + url + "' style='background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>View Original Article</a></p>" if url else ""}
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #888; font-size: 12px; text-align: center;">
                    Competitive Intelligence Alert System • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
                </p>
            </div>
        </body>
        </html>
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = ', '.join(self.email_to)
        
        # Add HTML part
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Send email
        try:
            server = smtplib.SMTP(self.email_smtp_host, self.email_smtp_port)
            server.starttls()
            server.login(self.email_username, self.email_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            self.logger.error(f"Email sending failed: {e}")
            return False
    
    def send_daily_summary(self, updates: List[Dict[str, Any]]) -> bool:
        """Send a daily summary of all competitive updates."""
        
        if not updates:
            return True
        
        # Count by priority and competitor
        summary_stats = {
            'total': len(updates),
            'high_priority': len([u for u in updates if u.get('strategic_priority') == 'high']),
            'by_competitor': {},
            'by_category': {}
        }
        
        for update in updates:
            competitor = update.get('competitor_name', 'Unknown')
            category = update.get('relevance_category', 'other')
            
            summary_stats['by_competitor'][competitor] = summary_stats['by_competitor'].get(competitor, 0) + 1
            summary_stats['by_category'][category] = summary_stats['by_category'].get(category, 0) + 1
        
        # Send Slack summary
        if self.slack_webhook:
            self._send_slack_daily_summary(summary_stats, updates)
        
        return True
    
    def _send_slack_daily_summary(self, stats: Dict[str, Any], updates: List[Dict[str, Any]]):
        """Send daily summary to Slack."""
        
        competitor_list = "\n".join([f"• {name}: {count}" for name, count in stats['by_competitor'].items()])
        category_list = "\n".join([f"• {name.replace('_', ' ').title()}: {count}" for name, count in stats['by_category'].items()])
        
        slack_payload = {
            "text": f"📊 Daily Competitive Intelligence Summary",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Competitive Intelligence Summary"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Updates:* {stats['total']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*High Priority:* {stats['high_priority']}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*By Competitor:*\n{competitor_list}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*By Category:*\n{category_list}"
                        }
                    ]
                }
            ]
        }
        
        requests.post(self.slack_webhook, json=slack_payload, timeout=10)

# Integration function to be called from your Flask app
def trigger_alert_for_approved_update(update_id: str):
    """
    Trigger alert when a high-priority update is approved.
    Call this from your Flask app's approval workflow.
    """
    from app_postgres import app, db, CompetitorUpdate, Competitor
    
    alerting_service = AlertingService()
    
    with app.app_context():
        # Get the approved update with competitor info
        update = db.session.query(CompetitorUpdate).join(Competitor).filter(
            CompetitorUpdate.id == update_id,
            CompetitorUpdate.strategic_priority == 'high'
        ).first()
        
        if not update:
            return False
        
        # Prepare alert data
        alert_data = {
            'competitor_name': update.competitor.name,
            'title': update.title,
            'summary': update.summary or update.ai_summary,
            'url': update.url,
            'strategic_priority': update.strategic_priority,
            'relevance_category': update.relevance_category,
            'confidence_score': update.confidence_score,
            'approved_by': update.approved_by_user.name if hasattr(update, 'approved_by_user') else 'Unknown',
            'approved_at': update.approved_at
        }
        
        # Send alert
        return alerting_service.send_high_priority_alert(alert_data)

if __name__ == "__main__":
    # Test the alerting service
    service = AlertingService()
    
    test_data = {
        'competitor_name': 'Snowflake',
        'title': 'Snowflake Announces Major Partnership with AWS',
        'summary': 'Snowflake has announced a strategic partnership with AWS to provide enhanced data sharing capabilities...',
        'url': 'https://example.com/news',
        'strategic_priority': 'high',
        'relevance_category': 'partnership',
        'confidence_score': 95,
        'approved_by': 'Test User'
    }
    
    result = service.send_high_priority_alert(test_data)
    print(f"Alert sent: {result}")
