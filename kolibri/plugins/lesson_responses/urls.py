from django.urls import re_path

from .views import free_math

urlpatterns = [re_path(r"^free_math/$", free_math, name="free_math")]
