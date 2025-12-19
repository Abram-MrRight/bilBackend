# dashboard/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def startswith(text, starts):
    """Returns True if text starts with the given string"""
    if not text:
        return False
    return text.startswith(starts)
