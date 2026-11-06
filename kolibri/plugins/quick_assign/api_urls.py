from django.urls import include
from django.urls import re_path
from rest_framework import routers

from .viewsets import JoinLinkViewset
from .viewsets import QuickAssignmentViewset

router = routers.SimpleRouter()
router.register(r"quickassignment", QuickAssignmentViewset, basename="quickassignment")
router.register(r"joinlink", JoinLinkViewset, basename="joinlink")

urlpatterns = [re_path(r"^", include(router.urls))]
