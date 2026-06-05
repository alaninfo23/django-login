from django import template

register = template.Library()

@register.filter
def brl(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    integer, decimal = f'{value:,.2f}'.split('.')
    return f"R$ {integer.replace(',', '.')},{decimal}"
