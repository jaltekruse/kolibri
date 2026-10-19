"""
The links coaches share, which are short and the same in every language.
"""

from django.shortcuts import redirect
from django.urls import re_path
from django.urls import reverse

JOIN_LINK_URL_NAME = "quick_assign_join_link"


def join_link(request, token):
    """Opens the join page, in the visitor's language, for the link's assignment."""
    return redirect(f"{reverse('kolibri:kolibri.plugins.quick_assign:join')}#/{token}")


urlpatterns = [
    re_path(r"^join/(?P<token>[\w-]+)/?$", join_link, name=JOIN_LINK_URL_NAME)
]
