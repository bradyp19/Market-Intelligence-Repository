"""
Main script for the Market Intelligence Agent.
"""

import os
import logging
import json
from datetime import datetime
from orchestrator import AgentOrchestrator

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

def main():
    """Main entry point for the Market Intelligence Agent."""
    try:
        # Initialize orchestrator
        orchestrator = AgentOrchestrator()
        
        # Process all companies
        logger.info("Starting announcement processing")
        results = orchestrator.process_all_companies()
        
        # Generate reports
        logger.info("Generating reports")
        quality_report = orchestrator.get_quality_report()
        coverage_report = orchestrator.get_coverage_report()
        
        # Save reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_report(quality_report, f'quality_report_{timestamp}.json')
        save_report(coverage_report, f'coverage_report_{timestamp}.json')
        
        # Log summary
        total_companies = len(results)
        total_announcements = sum(len(announcements) for announcements in results.values())
        logger.info(f"Processing complete. Found {total_announcements} announcements from {total_companies} companies.")
        
        # Check for low confidence summaries
        low_confidence = quality_report.get('low_confidence_summaries', [])
        if low_confidence:
            logger.warning(f"Found {len(low_confidence)} summaries that need review:")
            for summary in low_confidence:
                logger.warning(f"- {summary['company']}: {summary['url']} (confidence: {summary['confidence_score']:.2f})")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise

if __name__ == '__main__':
    main() 