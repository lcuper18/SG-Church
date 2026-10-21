"""Pagination for lists that a view builds by hand (detail pages)."""

from django.core.paginator import Paginator

PER_PAGE = 50


def paginate(request, items, per_page=PER_PAGE):
    """The requested page of `items` (a queryset or a list). A bad or out-of-range
    ?page= gives the first or last page instead of an error. Put the result in the
    context as `page_obj` and include "partials/pagination.html"."""
    return Paginator(items, per_page).get_page(request.GET.get("page"))
