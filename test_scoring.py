#!/usr/bin/env python3
"""Test the new confidence scoring system."""

from monitoring import QualityChecker

def test_scoring():
    qc = QualityChecker()
    
    # Test cases
    test_cases = [
        {
            'name': 'AI Announcement',
            'summary': {
                'title': 'Snowflake Announces New AI Features',
                'content': 'Today, Snowflake announced the general availability of new AI capabilities including machine learning features and enhanced data processing. The new features include improved performance and scalability for enterprise customers with advanced analytics.',
                'features': ['AI capabilities', 'ML features', 'Enhanced performance'],
                'url': 'https://snowflake.com/blog/ai-announcement'
            }
        },
        {
            'name': 'Privacy Policy',
            'summary': {
                'title': 'Privacy Policy',
                'content': 'This privacy policy explains how we collect data.',
                'features': [],
                'url': 'https://snowflake.com/privacy'
            }
        },
        {
            'name': 'Short Product Update',
            'summary': {
                'title': 'Product Update',
                'content': 'New release available.',
                'features': ['New release'],
                'url': 'https://company.com/blog/update'
            }
        },
        {
            'name': 'Detailed Technical Announcement',
            'summary': {
                'title': 'Major Platform Release',
                'content': 'We are excited to announce the launch of our new enterprise data platform featuring advanced API integrations, enhanced security compliance, improved scalability architecture, and comprehensive analytics capabilities. This release includes machine learning acceleration, cloud-native performance optimizations, and extensive developer SDK support.',
                'features': ['API integrations', 'Security compliance', 'ML acceleration', 'SDK support'],
                'url': 'https://company.com/blog/platform-release'
            }
        }
    ]
    
    print("Testing new confidence scoring system:")
    print("=" * 50)
    
    for test in test_cases:
        result = qc.check_summary_quality(test['summary'])
        score = result['confidence_score']
        needs_review = result['needs_review']
        
        print(f"{test['name']}: {score:.3f} {'(REVIEW)' if needs_review else '(OK)'}")
        
        if 'score_breakdown' in result:
            breakdown = result['score_breakdown']
            print(f"  Base: {breakdown['base']:.2f}, Content: {breakdown['content']:.2f}, "
                  f"Relevance: {breakdown['relevance']:.2f}, Depth: {breakdown['depth']:.2f}, "
                  f"Structure: {breakdown['structure']:.2f}")
        
        if result.get('reason'):
            print(f"  Reason: {result['reason']}")
        
        print()

if __name__ == '__main__':
    test_scoring()
