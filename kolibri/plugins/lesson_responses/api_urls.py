from django.urls import include
from django.urls import re_path
from rest_framework import routers

from .viewsets import LessonResponseViewset
from .viewsets import LessonWebPageViewset

router = routers.SimpleRouter()
router.register(r"lessonresponse", LessonResponseViewset, basename="lessonresponse")
router.register(r"lessonwebpage", LessonWebPageViewset, basename="lessonwebpage")

urlpatterns = [re_path(r"^", include(router.urls))]
