from typing import ClassVar

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers

from kolibri.core.api import ValuesViewset
from kolibri.core.auth.permissions import KolibriAuthPermissions
from kolibri.core.auth.permissions import KolibriAuthPermissionsFilter
from kolibri.utils.time_utils import local_now

from ..models import ContentFeedbackLog
from .filters import BaseLogFilter


class ContentFeedbackLogFilter(BaseLogFilter):
    class Meta:
        model = ContentFeedbackLog
        fields: ClassVar[list] = ["content_id", "user"]


class ContentFeedbackLogSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(required=False)

    class Meta:
        model = ContentFeedbackLog
        fields = ("id", "user", "content_id", "channel_id", "data", "updated")
        read_only_fields = ("id", "updated")

    def create(self, validated_data):
        # There is one for each content item for each learner, so giving feedback again replaces it
        feedback, _ = ContentFeedbackLog.objects.update_or_create(
            user=validated_data["user"],
            content_id=validated_data["content_id"],
            defaults={
                "channel_id": validated_data.get("channel_id"),
                "data": validated_data.get("data", {}),
                "updated": local_now(),
            },
        )
        return feedback

    def update(self, instance, validated_data):
        validated_data["updated"] = local_now()
        return super().update(instance, validated_data)


class ContentFeedbackLogViewSet(ValuesViewset):
    permission_classes = (KolibriAuthPermissions,)
    filter_backends = (KolibriAuthPermissionsFilter, DjangoFilterBackend)
    queryset = ContentFeedbackLog.objects.all().order_by("-updated")
    filterset_class = ContentFeedbackLogFilter
    serializer_class = ContentFeedbackLogSerializer
