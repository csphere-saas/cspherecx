def get_sentiment_choices():
    """
    Get sentiment choices for filters
    """
    return [
        ('POSITIVE', 'Positive'),
        ('NEGATIVE', 'Negative'),
        ('NEUTRAL', 'Neutral'),
        ('MIXED', 'Mixed'),
    ]

def get_analysis_status_choices():
    """
    Get analysis status choices for filters
    """
    return [
        ('analyzed', 'Analyzed'),
        ('not_analyzed', 'Not Analyzed'),
        ('needs_review', 'Needs Review'),
    ]