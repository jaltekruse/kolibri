from django.urls import re_path

from .views import JoinPageView

urlpatterns = [re_path(r"^$", JoinPageView.as_view(), name="join")]
