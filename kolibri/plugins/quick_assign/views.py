from django.views.generic.base import TemplateView

from kolibri.core.decorators import cache_no_user_data


@cache_no_user_data
class JoinPageView(TemplateView):
    """Where people who were sent a quick assignment's link give their name."""

    template_name = "quick_assign/quick_assign.html"
