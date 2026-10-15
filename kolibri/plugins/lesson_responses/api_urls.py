from django.urls import include
from django.urls import re_path
from rest_framework import routers

from .viewsets import LessonResponseViewset

router = routers.SimpleRouter()
router.register(r"lessonresponse", LessonResponseViewset, basename="lessonresponse")

urlpatterns = [re_path(r"^", include(router.urls))]
