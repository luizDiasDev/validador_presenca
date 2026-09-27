import markdown as md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(value):
    html = md.markdown(value, extensions=["extra"])
    return mark_safe(html)