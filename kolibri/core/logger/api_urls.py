from rest_framework import routers

from .viewsets.attempt_log import AttemptLogViewSet
from .viewsets.content_feedback_log import ContentFeedbackLogViewSet
from .viewsets.content_summary_log import ContentSummaryLogViewSet
from .viewsets.csv_log_request import GenerateCSVLogRequestViewSet
from .viewsets.mastery_log import MasteryLogViewSet
from .viewsets.progress_tracking import ProgressTrackingViewSet
from .viewsets.progress_tracking import TotalContentProgressViewSet

router = routers.SimpleRouter()

router.register(r"masterylog", MasteryLogViewSet, basename="masterylog")
router.register(r"attemptlog", AttemptLogViewSet, basename="attemptlog")
router.register(
    r"contentfeedbacklog", ContentFeedbackLogViewSet, basename="contentfeedbacklog"
)
router.register(
    r"contentsummarylog", ContentSummaryLogViewSet, basename="contentsummarylog"
)
router.register(r"userprogress", TotalContentProgressViewSet, basename="userprogress")
router.register(r"trackprogress", ProgressTrackingViewSet, basename="trackprogress")
router.register(
    r"generatecsvlogrequest",
    GenerateCSVLogRequestViewSet,
    basename="generatecsvlogrequest",
)

urlpatterns = router.urls
