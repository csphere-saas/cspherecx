from django import template

register = template.Library()

@register.filter
def sentiment_color(sentiment_score):
    """Convert sentiment score to Bootstrap color class"""
    if sentiment_score > 0.1:
        return "success"
    elif sentiment_score < -0.1:
        return "danger"
    else:
        return "secondary"

@register.filter
def sentiment_icon(sentiment_score):
    """Convert sentiment score to icon class"""
    if sentiment_score > 0.1:
        return "fa-smile"
    elif sentiment_score < -0.1:
        return "fa-frown"
    else:
        return "fa-meh"

@register.filter
def sentiment_text(sentiment_score):
    """Convert sentiment score to text"""
    if sentiment_score > 0.1:
        return "Positive"
    elif sentiment_score < -0.1:
        return "Negative"
    else:
        return "Neutral"