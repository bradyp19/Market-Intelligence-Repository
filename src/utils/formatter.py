"""
Formatting module for the Market Intelligence Agent.
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
import glob
import shutil
from dateutil.parser import parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SummaryFormatter:
    def __init__(self, output_dir: str = 'summaries'):
        """Initialize the formatter with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def format_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Format the summary for an announcement in the required structure."""
        try:
            title = analysis.get('title', 'Untitled')
            company = analysis.get('company', '')
            date = analysis.get('date')
            url = analysis.get('url', '')
            summary_text = analysis.get('summary', '')
            features = analysis.get('features', [])
            # Format date
            if date:
                if isinstance(date, str):
                    from dateutil.parser import parse
                    date_obj = parse(date, fuzzy=True)
                else:
                    date_obj = date
                date_str = date_obj.strftime('%Y-%m-%d')
            else:
                date_str = ''
            # Headline
            headline = f"{title} ({company}, {date_str})"
            # Source
            source = f"Source: {url}"
            # Summary (one or two sentences)
            summary = f"Summary: {summary_text.strip()}"
            # Key Features (themed, if possible)
            key_features = "Key Features:"
            if features and isinstance(features, list):
                for feat in features:
                    # Try to split into theme and description if possible
                    if ':' in feat:
                        theme, desc = feat.split(':', 1)
                        key_features += f"\n• {theme.strip()}: {desc.strip()}"
                    else:
                        key_features += f"\n• {feat.strip()}"
            else:
                key_features += "\n• No specific features identified."
            # Executive Insight (placeholder logic)
            exec_insight = "Executive Insight: This announcement highlights new capabilities or strategic direction relevant to customers or the business."
            # Compose markdown
            md = f"{headline}\n{source}\n{summary}\n{key_features}\n{exec_insight}\n"
            return {
                'formatted': md
            }
        except Exception as e:
            logger.error(f"Error formatting summary: {str(e)}")
            return {'formatted': 'Error formatting summary.'}

    def _format_features(self, features: list) -> str:
        """Format feature list."""
        try:
            if not features:
                return "No specific features identified."
            
            return "### Key Features\n" + "\n".join([
                f"- {feature}"
                for feature in features
            ])
        except Exception as e:
            logger.error(f"Error formatting features: {str(e)}")
            return "Error formatting features"

    def save_summary(self, company: str, analysis: Dict[str, Any]) -> str:
        """Save the formatted summary to a markdown file."""
        try:
            # Create filename from title
            filename = analysis['title'].lower()
            filename = ''.join(c if c.isalnum() else '_' for c in filename)
            filename = f"{filename[:50]}.md"
            
            # Create company directory
            company_dir = os.path.join(self.output_dir, company.lower())
            os.makedirs(company_dir, exist_ok=True)
            
            # Save file
            filepath = os.path.join(company_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.format_summary(analysis)['formatted'])
            
            return filepath
        except Exception as e:
            logger.error(f"Error saving summary: {str(e)}")
            return None

def clean_summaries(max_per_company=3):
    """Keep only the most recent and highest-confidence summaries (max 3 per company)."""
    summaries_root = 'summaries'
    if not os.path.exists(summaries_root):
        return
    for company in os.listdir(summaries_root):
        company_dir = os.path.join(summaries_root, company)
        if not os.path.isdir(company_dir):
            continue
        summary_files = glob.glob(os.path.join(company_dir, '*.md'))
        summary_infos = []
        for file in summary_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Try to extract confidence and date
                confidence = 0.0
                date = None
                # Confidence: look for 'confidence:' or 'Confidence:'
                for line in content.splitlines():
                    if 'confidence:' in line.lower():
                        try:
                            confidence = float(line.split(':')[-1].strip())
                        except Exception:
                            confidence = 0.0
                    if line.lower().startswith('**date:**'):
                        try:
                            date_str = line.split('**Date:**')[-1].strip()
                            date = parse(date_str, fuzzy=True)
                        except Exception:
                            date = None
                # If date is None, use file mtime as datetime
                if not date:
                    date = datetime.fromtimestamp(os.path.getmtime(file))
                summary_infos.append({
                    'file': file,
                    'confidence': confidence,
                    'date': date
                })
            except Exception:
                continue
        # Sort by confidence desc, then date desc
        summary_infos.sort(key=lambda x: (x['confidence'], x['date']), reverse=True)
        # Keep only top N
        to_keep = set(x['file'] for x in summary_infos[:max_per_company])
        for info in summary_infos[max_per_company:]:
            try:
                os.remove(info['file'])
            except Exception:
                pass 