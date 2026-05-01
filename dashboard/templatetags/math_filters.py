from django import template

register = template.Library()

@register.filter
def intdivide(value, arg):
    """
    Performs integer division (floor division).
    Example: 10|intdivide:3 → 3
    """
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return None
