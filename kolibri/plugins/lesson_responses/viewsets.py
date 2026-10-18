from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from kolibri.core.api import HexUUIDField
from kolibri.core.api import ReadOnlyValuesViewset
from kolibri.core.api import ValuesViewset
from kolibri.core.auth.constants import role_kinds
from kolibri.core.auth.permissions import KolibriAuthPermissions
from kolibri.core.auth.permissions import KolibriAuthPermissionsFilter
from kolibri.core.lessons.models import Lesson
from kolibri.core.logger.models import AttemptLog
from kolibri.core.logger.models import ContentSessionLog
from kolibri.core.logger.models import ContentSummaryLog
from kolibri.core.logger.models import MasteryLog
from kolibri.utils.time_utils import local_now

from .models import LessonWebPage
from .models import validate_web_page_url
from .utils import ANSWER_KEY
from .utils import expand_problem_numbers
from .utils import get_response_content_id
from .utils import MAX_ANSWER_LENGTH
from .utils import RESPONSE_KIND
from .utils import RESPONSE_MASTERY_LEVEL


class LessonItemSerializer(serializers.Serializer):
    lesson_id = HexUUIDField()
    # The contentnode_id of a lesson resource, or the id of a lesson web page
    item_id = HexUUIDField()


def free_math_document_field():
    """A base64 encoded Free Math document, blank for no answer."""
    return serializers.RegexField(
        r"^[A-Za-z0-9+/]*={0,2}$", allow_blank=True, max_length=MAX_ANSWER_LENGTH
    )


class SaveAnswersSerializer(LessonItemSerializer):
    # Keyed by prompt id
    answers = serializers.DictField(child=free_math_document_field())
    submit = serializers.BooleanField(default=False)


class GradeSerializer(LessonItemSerializer):
    # Keyed by learner id, then prompt id
    grades = serializers.DictField(
        child=serializers.DictField(child=free_math_document_field())
    )


class LessonResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptLog
        fields = ("id", "user", "item", "answer", "complete", "end_timestamp")


@dataclass(frozen=True)
class _LessonItem:
    """Something in a lesson that learners answer prompts about."""

    id: str
    prompt_ids: frozenset
    # The channel the logs record, for resources from a channel
    channel_id: Optional[str]
    # Saved on the session log, so exports can name what the answers are about
    context: dict


def _get_responses(lesson_id, item_id):
    content_id = get_response_content_id(lesson_id, item_id)
    return AttemptLog.objects.filter(
        masterylog__summarylog__content_id=content_id
    ).order_by("user_id", "item")


def _get_lesson_item(lesson, item_id):
    """
    A lesson resource with coach-written prompts, whose prompt ids are its
    prompts' ids, or a lesson web page, whose prompt ids are its problem numbers.
    """
    for resource in lesson.resources:
        if resource["contentnode_id"] == item_id and resource.get("prompts"):
            return _LessonItem(
                id=item_id,
                prompt_ids=frozenset(prompt["id"] for prompt in resource["prompts"]),
                channel_id=resource["channel_id"],
                # Same context keys as the progress tracking API
                context={"lesson_id": lesson.id, "node_id": item_id},
            )
    web_page = lesson.web_pages.filter(id=item_id).first()
    if web_page is not None:
        return _LessonItem(
            id=item_id,
            prompt_ids=frozenset(web_page.problems),
            channel_id=None,
            context={"lesson_id": lesson.id, "web_page_id": item_id},
        )
    raise ValidationError({"item_id": "This lesson has no prompts on this item"})


def _validate_prompt_ids(item, prompt_ids, field):
    if not item.prompt_ids.issuperset(prompt_ids):
        raise ValidationError({field: "Answers must be for this item's prompts"})


def _get_or_create_sessionlog(user, item, content_id, now):
    sessionlog = (
        ContentSessionLog.objects.filter(user=user, content_id=content_id)
        .order_by("-start_timestamp")
        .first()
    )
    if sessionlog is None:
        sessionlog = ContentSessionLog.objects.create(
            user=user,
            content_id=content_id,
            channel_id=item.channel_id,
            kind=RESPONSE_KIND,
            start_timestamp=now,
            extra_fields={"context": item.context},
        )
    return sessionlog


def _save_answers(user, lesson_id, item, answers, submit):
    now = local_now()
    content_id = get_response_content_id(lesson_id, item.id)
    summarylog, _ = ContentSummaryLog.objects.get_or_create(
        user=user,
        content_id=content_id,
        defaults={
            "channel_id": item.channel_id,
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

    sessionlog = _get_or_create_sessionlog(user, item, content_id, now)
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
    Answers to the prompts on one lesson item, filtered by the required
    ``lesson_id`` and ``item_id`` query parameters: the questions on a lesson
    resource, or the problems listed for a lesson web page. Each answer is a Free
    Math document, which also holds the coach's grading.
    Learners see their own answers; coaches see their learners' answers.
    """

    permission_classes = (IsAuthenticated, KolibriAuthPermissions)
    filter_backends = (KolibriAuthPermissionsFilter,)
    serializer_class = LessonResponseSerializer

    def get_queryset(self):
        params = LessonItemSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return _get_responses(**params.validated_data)

    @action(detail=False, methods=["post"], permission_classes=(IsAuthenticated,))
    def save(self, request):
        """
        Save the requesting learner's answers, keyed by prompt id, and
        optionally submit them. Submitted answers can no longer be changed.
        Returns the learner's answers for this lesson item.
        """
        serializer = SaveAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson_id = serializer.validated_data["lesson_id"]
        item_id = serializer.validated_data["item_id"]
        answers = serializer.validated_data["answers"]

        lesson = get_object_or_404(
            Lesson.objects.filter(
                is_active=True,
                lesson_assignments__collection__membership__user=request.user,
            ).distinct(),
            id=lesson_id,
        )
        item = _get_lesson_item(lesson, item_id)
        _validate_prompt_ids(item, answers, "answers")

        with transaction.atomic():
            _save_answers(
                request.user,
                lesson_id,
                item,
                answers,
                serializer.validated_data["submit"],
            )
        return Response(
            self.serialize(_get_responses(lesson_id, item_id).filter(user=request.user))
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
        item_id = serializer.validated_data["item_id"]
        grades = serializer.validated_data["grades"]

        lesson = get_object_or_404(Lesson, id=lesson_id)
        item = _get_lesson_item(lesson, item_id)
        attemptlogs = {
            (attemptlog.user_id, attemptlog.item): attemptlog
            for attemptlog in _get_responses(lesson_id, item_id)
            .filter(user_id__in=grades)
            .select_related("user")
        }
        for user_id, documents in grades.items():
            _validate_prompt_ids(item, documents, "grades")
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


class LessonWebPageSerializer(serializers.ModelSerializer):
    lesson = serializers.PrimaryKeyRelatedField(queryset=Lesson.objects.all())
    # DRF leaves out the model field's URL validator in favour of its own,
    # which also allows ftp
    url = serializers.URLField(max_length=2000, validators=[validate_web_page_url])
    # The problem numbers listed in problem_numbers, one by one
    problems = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = LessonWebPage
        fields = (
            "id",
            "lesson",
            "title",
            "url",
            "instructions",
            "problem_numbers",
            "problems",
        )
        read_only_fields = ("id",)

    def validate_problem_numbers(self, value):
        try:
            expand_problem_numbers(value)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return value

    def update(self, instance, validated_data):
        # A web page stays in the lesson it was added to
        validated_data.pop("lesson", None)
        return super().update(instance, validated_data)


class LessonWebPagePermissions(BasePermission):
    """
    Coaches and admins who can edit a lesson can change its web pages. Who can
    read them is decided by LessonWebPageViewset.get_queryset.
    """

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or request.user.can_update(obj.lesson)


class LessonWebPageViewset(ValuesViewset):
    """
    Web pages in lessons, filtered by the ``lesson`` query parameter.
    Coaches see the web pages in lessons they can see, and learners the ones in
    active lessons assigned to them.
    """

    permission_classes = (IsAuthenticated, LessonWebPagePermissions)
    serializer_class = LessonWebPageSerializer
    deferred_fields = ("problems",)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("lesson",)

    def get_queryset(self):
        user = self.request.user
        assigned_lessons = Lesson.objects.filter(
            is_active=True, lesson_assignments__collection__membership__user=user
        )
        return LessonWebPage.objects.filter(
            Q(lesson__in=user.filter_readable(Lesson.objects.all()))
            | Q(lesson__in=assigned_lessons)
        ).distinct()

    def consolidate(self, items, queryset):
        for item in items:
            item["problems"] = expand_problem_numbers(item["problem_numbers"])
        return items

    def perform_create(self, serializer):
        if not self.request.user.can_update(serializer.validated_data["lesson"]):
            raise PermissionDenied()
        serializer.save()
