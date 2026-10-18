from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kolibri.core.api import HexUUIDField
from kolibri.core.api import ReadOnlyValuesViewset
from kolibri.core.auth.constants import role_kinds
from kolibri.core.auth.permissions import KolibriAuthPermissions
from kolibri.core.auth.permissions import KolibriAuthPermissionsFilter
from kolibri.core.lessons.models import Lesson
from kolibri.core.logger.models import AttemptLog
from kolibri.core.logger.models import ContentSessionLog
from kolibri.core.logger.models import ContentSummaryLog
from kolibri.core.logger.models import MasteryLog
from kolibri.utils.time_utils import local_now

from .utils import ANSWER_KEY
from .utils import get_response_content_id
from .utils import MAX_ANSWER_LENGTH
from .utils import RESPONSE_KIND
from .utils import RESPONSE_MASTERY_LEVEL


class LessonResourceSerializer(serializers.Serializer):
    lesson_id = HexUUIDField()
    contentnode_id = HexUUIDField()


def free_math_document_field():
    """A base64 encoded Free Math document, blank for no answer."""
    return serializers.RegexField(
        r"^[A-Za-z0-9+/]*={0,2}$", allow_blank=True, max_length=MAX_ANSWER_LENGTH
    )


class SaveAnswersSerializer(LessonResourceSerializer):
    # Keyed by prompt id
    answers = serializers.DictField(child=free_math_document_field())
    submit = serializers.BooleanField(default=False)


class GradeSerializer(LessonResourceSerializer):
    # Keyed by learner id, then prompt id
    grades = serializers.DictField(
        child=serializers.DictField(child=free_math_document_field())
    )


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


def _validate_prompt_ids(resource, prompt_ids, field):
    if not {prompt["id"] for prompt in resource["prompts"]}.issuperset(prompt_ids):
        raise ValidationError({field: "Answers must be for this resource's prompts"})


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
    for prompt_id, document in answers.items():
        attemptlog = attemptlogs.get(prompt_id)
        if attemptlog is None:
            if not document:
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
        elif (attemptlog.answer or {}).get(ANSWER_KEY) == document:
            continue
        attemptlog.answer = {ANSWER_KEY: document}
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
    Answers to the prompts on one lesson resource, filtered by the required
    ``lesson_id`` and ``contentnode_id`` query parameters. Each answer is a Free
    Math document, which also holds the coach's grading.
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
        _validate_prompt_ids(resource, answers, "answers")

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

    @action(detail=False, methods=["post"], permission_classes=(IsAuthenticated,))
    def grade(self, request):
        """
        Save a coach's grading of learners' answers: for each learner, keyed by
        learner id, the Free Math documents of their answers with the coach's
        scores, feedback and highlights in them, keyed by prompt id.
        Only answers that learners have saved can be graded.
        """
        serializer = GradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson_id = serializer.validated_data["lesson_id"]
        contentnode_id = serializer.validated_data["contentnode_id"]
        grades = serializer.validated_data["grades"]

        lesson = get_object_or_404(Lesson, id=lesson_id)
        resource = _get_prompted_resource(lesson, contentnode_id)
        attemptlogs = {
            (attemptlog.user_id, attemptlog.item): attemptlog
            for attemptlog in _get_responses(lesson_id, contentnode_id)
            .filter(user_id__in=grades)
            .select_related("user")
        }
        for user_id, documents in grades.items():
            _validate_prompt_ids(resource, documents, "grades")
            for prompt_id in documents:
                attemptlog = attemptlogs.get((user_id, prompt_id))
                if attemptlog is None:
                    raise ValidationError(
                        {"grades": "Only saved answers can be graded"}
                    )
                if not request.user.has_role_for_user(
                    (role_kinds.ADMIN, role_kinds.COACH), attemptlog.user
                ):
                    raise PermissionDenied()

        with transaction.atomic():
            for user_id, documents in grades.items():
                for prompt_id, document in documents.items():
                    attemptlog = attemptlogs[(user_id, prompt_id)]
                    attemptlog.answer = {ANSWER_KEY: document}
                    attemptlog.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
