from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)

@register.filter
def get_first_value(dictionary):
    """Get first value from dictionary"""
    if dictionary and isinstance(dictionary, dict):
        values = list(dictionary.values())
        return values[0] if values else None
    return None