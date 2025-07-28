"""
Main script for the Market Intelligence Agent with date range support.
"""

import os
import logging
import json
import argparse
from datetime import datetime, timedelta
from orchestrator import AgentOrchestrator
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_report(report: dict, filename: str):
    """Save a report to a JSON file."""
    try:
        os.makedirs('reports', exist_ok=True)
        filepath = os.path.join('reports', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Saved report to {filepath}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")

def modify_date_filter(from_date: datetime, to_date: datetime):
    """Temporarily modify the date filter in config."""
    # Store original value
    original_date = config.MIN_PUBLISH_DATE
    
    # Set new date filter to capture content from the specified range
    # Allow a buffer to catch articles that might be slightly outside the range
    buffer_days = 7
    config.MIN_PUBLISH_DATE = from_date - timedelta(days=buffer_days)
    logger.info(f"Set date filter from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')} (with {buffer_days} day buffer)")
    
    return original_date

def restore_date_filter(original_date):
    """Restore original date filter."""
    config.MIN_PUBLISH_DATE = original_date

def main(from_date_str: str = None, to_date_str: str = None):
    """Main entry point for the Market Intelligence Agent with date range."""
    
    # Parse dates
    if from_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
    else:
        from_date = datetime(2025, 7, 16)  # Default to July 16, 2025
        
    if to_date_str:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
    else:
        to_date = datetime(2025, 7, 21)  # Default to July 21, 2025 (today)
    
    logger.info(f"Running Market Intelligence Agent from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
    
    # Temporarily modify date filter
    original_date = modify_date_filter(from_date, to_date)
    
    try:
        # Initialize orchestrator
        orchestrator = AgentOrchestrator()
        
        # Process all companies
        logger.info("Starting announcement processing")
        results = orchestrator.process_all_companies()
        
        # Filter results by date range
        filtered_results = {}
        for company, announcements in results.items():
            filtered_announcements = []
            for announcement in announcements:
                announcement_date = announcement.get('date')
                if isinstance(announcement_date, str):
                    try:
                        announcement_date = datetime.fromisoformat(announcement_date.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        continue
                elif not isinstance(announcement_date, datetime):
                    continue
                    
                # Check if announcement is in date range
                if from_date <= announcement_date <= to_date + timedelta(days=1):
                    filtered_announcements.append(announcement)
            
            if filtered_announcements:
                filtered_results[company] = filtered_announcements
        
        # Generate reports
        logger.info("Generating reports")
        quality_report = orchestrator.get_quality_report()
        coverage_report = orchestrator.get_coverage_report()
        
        # Add date range info to reports
        date_range_info = {
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'total_days': (to_date - from_date).days + 1
        }
        quality_report['date_range'] = date_range_info
        coverage_report['date_range'] = date_range_info
        
        # Save reports with date range in filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        date_suffix = f"{from_date.strftime('%Y%m%d')}_to_{to_date.strftime('%Y%m%d')}"
        save_report(quality_report, f'quality_report_{date_suffix}_{timestamp}.json')
        save_report(coverage_report, f'coverage_report_{date_suffix}_{timestamp}.json')
        
        # Log summary
        total_companies = len(filtered_results)
        total_announcements = sum(len(announcements) for announcements in filtered_results.values())
        logger.info(f"Processing complete for date range {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
        logger.info(f"Found {total_announcements} announcements from {total_companies} companies.")
        
        # Show filtered results summary
        if filtered_results:
            logger.info("Announcements found by company:")
            for company, announcements in filtered_results.items():
                logger.info(f"  {company}: {len(announcements)} announcements")
                for ann in announcements:
                    logger.info(f"    - {ann['title'][:80]}... ({ann['date']})")
        else:
            logger.info("No announcements found in the specified date range.")
        
        # Check for low confidence summaries
        low_confidence = quality_report.get('low_confidence_summaries', [])
        if low_confidence:
            logger.warning(f"Found {len(low_confidence)} summaries that need review:")
            for summary in low_confidence:
                logger.warning(f"- {summary['company']}: {summary['url']} (confidence: {summary['confidence_score']:.2f})")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise
    finally:
        # Restore original date filter
        restore_date_filter(original_date)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Market Intelligence Agent with date range support')
    parser.add_argument('--from-date', type=str, help='Start date (YYYY-MM-DD)', default='2025-07-16')
    parser.add_argument('--to-date', type=str, help='End date (YYYY-MM-DD)', default='2025-07-21')
    
    args = parser.parse_args()
    main(args.from_date, args.to_date)
