"""Member search shared by the list page, the lookup endpoint and pickers."""

from core.text import fold


def search_members(queryset, text):
    """Keep members matching *every* word of `text`, ignoring case and accents,
    against name, e-mail and phone ("maria garcia" finds "María García")."""
    for term in fold(text).split():
        queryset = queryset.filter(search_text__contains=term)
    return queryset
