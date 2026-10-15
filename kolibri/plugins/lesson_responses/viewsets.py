from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kolibri.core.api import HexUUIDField
from kolibri.core.api import ReadOnlyValuesViewset
from kolibri.core.api import ValuesViewset
from kolibri.core.auth.permissions import KolibriAuthPermissions
from kolibri.core.auth.permissions import KolibriAuthPermissionsFilter
from kolibri.core.lessons.models import Lesson
from kolibri.core.logger.models import AttemptLog
from kolibri.core.logger.models import ContentSessionLog
from kolibri.core.logger.models import ContentSummaryLog
from kolibri.core.logger.models import MasteryLog
from kolibri.utils.time_utils import local_now

from .models import LessonResponseFeedback
from .utils import get_response_content_id
from .utils import MAX_ANSWER_LENGTH
from .utils import MAX_COMMENT_LENGTH
from .utils import RESPONSE_KIND
from .utils import RESPONSE_MASTERY_LEVEL
from .utils import SIMPLE_ANSWER_LENGTH


class LessonResourceSerializer(serializers.Serializer):
    lesson_id = HexUUIDField()
    contentnode_id = HexUUIDField()


class SaveAnswersSerializer(LessonResourceSerializer):
    # Keyed by prompt id
    answers = serializers.DictField(
        child=serializers.CharField(
            allow_blank=True, trim_whitespace=False, max_length=MAX_ANSWER_LENGTH
        )
    )
    submit = serializers.BooleanField(default=False)


class LessonResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptLog
        fields = ("id", "user", "item", "answer", "complete", "end_timestamp")


def _get_responses(lesson_id, contentnode_id):
    content_id = get_response_content_id(lesson_id, contentnode_id)
    return AttemptLog.objects.filter(
        masterylog__summarylog__content_id=content_id
    ).order_by("user_id", "item")


def _get_prompted_resource(lesson, contentnode_id):
    for resource in lesson.resources:
        if resource["contentnode_id"] == contentnode_id and resource.get("prompts"):
            return resource
    raise ValidationError({"contentnode_id": "This lesson resource has no prompts"})


def _get_or_create_sessionlog(user, lesson_id, resource, content_id, now):
    sessionlog = (
        ContentSessionLog.objects.filter(user=user, content_id=content_id)
        .order_by("-start_timestamp")
        .first()
    )
    if sessionlog is None:
        sessionlog = ContentSessionLog.objects.create(
            user=user,
            content_id=content_id,
            channel_id=resource["channel_id"],
            kind=RESPONSE_KIND,
            start_timestamp=now,
            # Same context keys as the progress tracking API, so exports
            # can name the resource these responses are about.
            extra_fields={
                "context": {
                    "lesson_id": lesson_id,
                    "node_id": resource["contentnode_id"],
                }
            },
        )
    return sessionlog


def _save_answers(user, lesson_id, resource, answers, submit):
    now = local_now()
    content_id = get_response_content_id(lesson_id, resource["contentnode_id"])
    summarylog, _ = ContentSummaryLog.objects.get_or_create(
        user=user,
        content_id=content_id,
        defaults={
            "channel_id": resource["channel_id"],
            "kind": RESPONSE_KIND,
            "start_timestamp": now,
        },
    )
    masterylog, _ = MasteryLog.objects.get_or_create(
        user=user,
        summarylog=summarylog,
        mastery_level=RESPONSE_MASTERY_LEVEL,
        defaults={"mastery_criterion": {"type": RESPONSE_KIND}, "start_timestamp": now},
    )
    if masterylog.complete:
        raise ValidationError("These responses have already been submitted")

    sessionlog = _get_or_create_sessionlog(user, lesson_id, resource, content_id, now)
    attemptlogs = {
        attemptlog.item: attemptlog for attemptlog in masterylog.attemptlogs.all()
    }
    for prompt_id, text in answers.items():
        attemptlog = attemptlogs.get(prompt_id)
        if attemptlog is None:
            if not text:
                continue
            attemptlog = AttemptLog(
                user=user,
                masterylog=masterylog,
                sessionlog=sessionlog,
                item=prompt_id,
                start_timestamp=now,
                correct=0,
            )
            attemptlogs[prompt_id] = attemptlog
        elif (attemptlog.answer or {}).get("text") == text:
            continue
        attemptlog.answer = {"text": text}
        attemptlog.simple_answer = text[:SIMPLE_ANSWER_LENGTH]
        attemptlog.end_timestamp = now
        attemptlog.save()

    if submit:
        for attemptlog in attemptlogs.values():
            attemptlog.complete = True
            attemptlog.completion_timestamp = now
            attemptlog.end_timestamp = now
            attemptlog.save()
        masterylog.complete = True
        masterylog.completion_timestamp = now
        summarylog.progress = 1
        summarylog.completion_timestamp = now

    masterylog.end_timestamp = now
    masterylog.save()
    summarylog.end_timestamp = now
    summarylog.save()
    sessionlog.end_timestamp = now
    sessionlog.save()


class LessonResponseViewset(ReadOnlyValuesViewset):
    """
    Free-text answers to the prompts on one lesson resource, filtered by the
    required ``lesson_id`` and ``contentnode_id`` query parameters.
    Learners see their own answers; coaches see their learners' answers.
    """

    permission_classes = (IsAuthenticated, KolibriAuthPermissions)
    filter_backends = (KolibriAuthPermissionsFilter,)
    serializer_class = LessonResponseSerializer

    def get_queryset(self):
        params = LessonResourceSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return _get_responses(**params.validated_data)

    @action(detail=False, methods=["post"], permission_classes=(IsAuthenticated,))
    def save(self, request):
        """
        Save the requesting learner's answers, keyed by prompt id, and
        optionally submit them. Submitted answers can no longer be changed.
        Returns the learner's answers for this lesson resource.
        """
        serializer = SaveAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson_id = serializer.validated_data["lesson_id"]
        contentnode_id = serializer.validated_data["contentnode_id"]
        answers = serializer.validated_data["answers"]

        lesson = get_object_or_404(
            Lesson.objects.filter(
                is_active=True,
                lesson_assignments__collection__membership__user=request.user,
            ).distinct(),
            id=lesson_id,
        )
        resource = _get_prompted_resource(lesson, contentnode_id)
        prompt_ids = {prompt["id"] for prompt in resource["prompts"]}
        if not prompt_ids.issuperset(answers):
            raise ValidationError(
                {"answers": "Answers must be for this resource's prompts"}
            )

        with transaction.atomic():
            _save_answers(
                request.user,
                lesson_id,
                resource,
                answers,
                serializer.validated_data["submit"],
            )
        return Response(
            self.serialize(
                _get_responses(lesson_id, contentnode_id).filter(user=request.user)
            )
        )


class LessonResponseFeedbackSerializer(serializers.ModelSerializer):
    lesson_id = HexUUIDField()
    contentnode_id = HexUUIDField()
    comment = serializers.CharField(
        allow_blank=True, required=False, max_length=MAX_COMMENT_LENGTH
    )
    # Keyed by prompt id
    prompt_comments = serializers.DictField(
        child=serializers.CharField(allow_blank=True, max_length=MAX_COMMENT_LENGTH),
        required=False,
    )

    class Meta:
        model = LessonResponseFeedback
        fields = (
            "id",
            "user",
            "lesson_id",
            "contentnode_id",
            "comment",
            "prompt_comments",
            "date_modified",
        )
        read_only_fields = ("id", "date_modified")

    def validate(self, attrs):
        lesson_id = attrs.get("lesson_id", getattr(self.instance, "lesson_id", None))
        contentnode_id = attrs.get(
            "contentnode_id", getattr(self.instance, "contentnode_id", None)
        )
        lesson = Lesson.objects.filter(id=lesson_id).first()
        if lesson is None:
            raise ValidationError({"lesson_id": "Lesson does not exist"})
        resource = _get_prompted_resource(lesson, contentnode_id)
        prompt_ids = {prompt["id"] for prompt in resource["prompts"]}
        if not prompt_ids.issuperset(attrs.get("prompt_comments", {})):
            raise ValidationError(
                {"prompt_comments": "Comments must be for this resource's prompts"}
            )
        return attrs

    def update(self, instance, validated_data):
        # These identify the feedback record, so they cannot change.
        for field in ("user", "lesson_id", "contentnode_id"):
            validated_data.pop(field, None)
        validated_data["date_modified"] = local_now()
        return super().update(instance, validated_data)


class LessonResponseFeedbackViewset(ValuesViewset):
    """
    Coach feedback on learners' answers to the prompts on a lesson resource.
    Listing requires the ``lesson_id`` and ``contentnode_id`` query parameters.
    Learners can read their own feedback; coaches can read and write feedback
    for learners in their classes.
    """

    permission_classes = (IsAuthenticated, KolibriAuthPermissions)
    filter_backends = (KolibriAuthPermissionsFilter,)
    serializer_class = LessonResponseFeedbackSerializer

    def get_queryset(self):
        queryset = LessonResponseFeedback.objects.order_by("user_id")
        if self.action != "list":
            return queryset
        params = LessonResourceSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return queryset.filter(**params.validated_data)
