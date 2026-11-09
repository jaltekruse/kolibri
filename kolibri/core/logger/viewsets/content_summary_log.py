from typing import ClassVar

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers

from kolibri.core.api import ReadOnlyValuesViewset
from kolibri.core.auth.permissions import KolibriAuthPermissions
from kolibri.core.auth.permissions import KolibriAuthPermissionsFilter
from kolibri.core.decorators import query_params_required

from ..models import ContentSummaryLog
from .filters import BaseLogFilter


class ContentSummaryLogFilter(BaseLogFilter):
    class Meta:
        model = ContentSummaryLog
        fields: ClassVar[list] = ["content_id", "user"]


class ContentSummaryLogSerializer(serializers.ModelSerializer):
    extra_fields = serializers.JSONField()

    class Meta:
        model = ContentSummaryLog
        fields = ("id", "user", "content_id", "progress", "extra_fields")


# Learners' work saved in a resource can be large, so it is only read for one resource at a time
@query_params_required(content_id=str)
class ContentSummaryLogViewSet(ReadOnlyValuesViewset):
    permission_classes = (KolibriAuthPermissions,)
    filter_backends = (KolibriAuthPermissionsFilter, DjangoFilterBackend)
    queryset = ContentSummaryLog.objects.all().order_by("user_id")
    filterset_class = ContentSummaryLogFilter
    serializer_class = ContentSummaryLogSerializer
