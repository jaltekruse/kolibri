from django.urls import include
from django.urls import re_path
from rest_framework import routers

from .viewsets import LessonResponseFeedbackViewset
from .viewsets import LessonResponseViewset

router = routers.SimpleRouter()
router.register(r"lessonresponse", LessonResponseViewset, basename="lessonresponse")
router.register(
    r"lessonresponsefeedback",
    LessonResponseFeedbackViewset,
    basename="lessonresponsefeedback",
)

urlpatterns = [re_path(r"^", include(router.urls))]
