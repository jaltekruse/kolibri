import hashlib
import hmac
import re
import secrets

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth import logout
from django.db import transaction
from django.db.models import Count
from django.db.models import OuterRef
from django.db.models import Subquery
from django.shortcuts import get_object_or_404
from django.urls import reverse
from le_utils.constants import content_kinds
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kolibri.core.api import HexUUIDField
from kolibri.core.api import ValuesMethodField
from kolibri.core.api import ValuesViewset
from kolibri.core.auth.constants import role_kinds
from kolibri.core.auth.constants.demographics import NOT_SPECIFIED
from kolibri.core.auth.models import AdHocGroup
from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.content.models import ContentNode
from kolibri.core.lessons.models import Lesson
from kolibri.core.lessons.models import LessonAssignment
from kolibri.plugins.lesson_responses.models import LessonWebPage
from kolibri.plugins.lesson_responses.viewsets import LessonWebPageSerializer

from .models import LinkLearner
from .models import QuickAssignClassroom
from .models import QuickAssignment
from .root_urls import JOIN_LINK_URL_NAME

# Holds "<user id>.<key>" for a learner who joined through a link
BROWSER_KEY_COOKIE = "kolibri_quick_assign"
BROWSER_KEY_MAX_AGE = 60 * 60 * 24 * 365

TITLE_MAX_LENGTH = Lesson._meta.get_field("title").max_length
FULL_NAME_MAX_LENGTH = FacilityUser._meta.get_field("full_name").max_length


def _can_quick_assign(user):
    return (
        user.is_superuser
        or user.roles.filter(kind__in=(role_kinds.ADMIN, role_kinds.COACH)).exists()
    )


class CanQuickAssign(BasePermission):
    def has_permission(self, request, view):
        return _can_quick_assign(request.user)


class QuickAssignWebPageSerializer(LessonWebPageSerializer):
    # The web page goes in the lesson made for it, with the lesson's title
    lesson = None
    problems = None

    class Meta(LessonWebPageSerializer.Meta):
        fields = ("url", "instructions", "problem_numbers")


class CreateQuickAssignmentSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=TITLE_MAX_LENGTH)
    # Exercises from the library, or a web page to show work on in Free Math
    exercise_ids = serializers.ListField(
        child=HexUUIDField(), required=False, allow_empty=False
    )
    web_page = QuickAssignWebPageSerializer(required=False)
    # For the coach's quick assignments class, if this is their first
    classroom_name = serializers.CharField(max_length=100)

    def validate(self, attrs):
        if ("exercise_ids" in attrs) == ("web_page" in attrs):
            raise ValidationError("Give either exercise_ids or web_page")
        return attrs

    def validate_exercise_ids(self, value):
        exercises = ContentNode.objects.filter(
            id__in=value, kind=content_kinds.EXERCISE, available=True
        ).in_bulk()
        missing = [node_id for node_id in value if node_id not in exercises]
        if missing:
            raise ValidationError(f"Not exercises in the library: {', '.join(missing)}")
        return [exercises[node_id] for node_id in value]


class UpdateQuickAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickAssignment
        fields = ("is_open",)


class QuickAssignmentSerializer(serializers.ModelSerializer):
    id = HexUUIDField(source="lesson_id", read_only=True)
    title = serializers.CharField(source="lesson.title", read_only=True)
    classroom_id = HexUUIDField(source="lesson.collection_id", read_only=True)
    date_created = serializers.DateTimeField(
        source="lesson.date_created", read_only=True
    )
    resources = serializers.JSONField(source="lesson.resources", read_only=True)
    # How many people joined through the link
    learner_count = serializers.IntegerField(read_only=True)
    # The web page learners work from in Free Math, for Free Math assignments
    web_page_id = HexUUIDField(read_only=True, allow_null=True)
    # The address to share
    link = ValuesMethodField(sources=("token",))

    class Meta:
        model = QuickAssignment
        fields = (
            "id",
            "title",
            "classroom_id",
            "date_created",
            "resources",
            "token",
            "is_open",
            "learner_count",
            "web_page_id",
            "link",
        )
        read_only_fields = ("token",)

    def get_link(self, obj):
        path = reverse(JOIN_LINK_URL_NAME, args=[obj.token])
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


def _classroom_for(coach, name):
    try:
        return coach.quick_assign_classroom.classroom
    except QuickAssignClassroom.DoesNotExist:
        pass
    classroom = Classroom.objects.create(name=name, parent=coach.facility)
    classroom.add_coach(coach)
    QuickAssignClassroom.objects.create(coach=coach, classroom=classroom)
    return classroom


def _unique_title(title, classroom):
    taken = set(
        Lesson.objects.filter(collection=classroom).values_list("title", flat=True)
    )
    candidate, number = title, 1
    while candidate in taken:
        number += 1
        suffix = f" ({number})"
        candidate = title[: TITLE_MAX_LENGTH - len(suffix)] + suffix
    return candidate


class QuickAssignmentViewset(ValuesViewset):
    """
    The quick assignments a coach made: lessons in their quick assignments class,
    which anyone with the link can join.
    """

    permission_classes = (IsAuthenticated, CanQuickAssign)
    serializer_class = QuickAssignmentSerializer
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        return QuickAssignment.objects.filter(lesson__created_by=self.request.user)

    def annotate_queryset(self, queryset):
        web_pages = LessonWebPage.objects.filter(lesson_id=OuterRef("lesson_id"))
        return queryset.annotate(
            learner_count=Count("group__membership", distinct=True),
            web_page_id=Subquery(web_pages.values("id")[:1]),
        ).order_by("-lesson__date_created")

    def create(self, request, *args, **kwargs):
        serializer = CreateQuickAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        coach = request.user
        with transaction.atomic():
            classroom = _classroom_for(coach, data["classroom_name"])
            title = _unique_title(data["title"], classroom)
            lesson = Lesson.objects.create(
                title=title,
                collection=classroom,
                created_by=coach,
                is_active=True,
                resources=[
                    {
                        "contentnode_id": node.id,
                        "content_id": node.content_id,
                        "channel_id": node.channel_id,
                    }
                    for node in data.get("exercise_ids", [])
                ],
            )
            group = AdHocGroup.objects.create(name=title, parent=classroom)
            LessonAssignment.objects.create(
                lesson=lesson, collection=group, assigned_by=coach
            )
            if "web_page" in data:
                LessonWebPage.objects.create(
                    lesson=lesson, title=title, **data["web_page"]
                )
            QuickAssignment.objects.create(lesson=lesson, group=group)
        return Response(self.serialize_object(pk=lesson.id), status=201)

    def partial_update(self, request, *args, **kwargs):
        quick_assignment = self.get_object()
        serializer = UpdateQuickAssignmentSerializer(
            quick_assignment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.serialize_object(pk=quick_assignment.pk))


def _key_hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def _remembered_learner(request):
    """The learner this browser joined as, from the key it keeps."""
    user_id, _, key = request.COOKIES.get(BROWSER_KEY_COOKIE, "").partition(".")
    link_learner = (
        LinkLearner.objects.select_related("user").filter(user_id=user_id).first()
        if user_id and key
        else None
    )
    if link_learner and hmac.compare_digest(link_learner.key_hash, _key_hash(key)):
        return link_learner.user
    return None


def _username_for(full_name):
    # Kolibri usernames are up to 30 letters, numbers and underscores
    base = re.sub(r"\W+", "_", full_name).strip("_")[:20] or "learner"
    return f"{base}_{secrets.token_hex(3)}"


class JoinSerializer(serializers.Serializer):
    # Blank to continue as the learner signed in or remembered by this browser
    full_name = serializers.CharField(
        max_length=FULL_NAME_MAX_LENGTH, required=False, allow_blank=True
    )


class JoinLinkViewset(viewsets.ViewSet):
    """
    Lets anyone with a quick assignment's link join it, by the link's token.
    Retrieving says what the link is for and who this browser would join as;
    the join action joins, as a new learner with the full name given, or else as
    that learner, and signs them in.
    """

    permission_classes = (AllowAny,)
    lookup_value_regex = r"[\w-]+"

    def get_quick_assignment(self, token):
        return get_object_or_404(
            QuickAssignment.objects.select_related(
                "lesson", "lesson__created_by", "group"
            ),
            token=token,
        )

    def current_learner(self, request, quick_assignment):
        """The learner already signed in, or remembered, and whether they are signed in."""
        user = request.user
        if isinstance(user, FacilityUser):
            # Learners can only join classes in their own facility
            if user.dataset_id == quick_assignment.group.dataset_id:
                return user, True
            return None, False
        return _remembered_learner(request), False

    def is_coach(self, request, quick_assignment):
        return request.user.is_authenticated and request.user.can_update(
            quick_assignment.lesson
        )

    def retrieve(self, request, pk):
        quick_assignment = self.get_quick_assignment(pk)
        learner, is_signed_in = self.current_learner(request, quick_assignment)
        return Response(
            {
                "title": quick_assignment.lesson.title,
                "coach_name": quick_assignment.lesson.created_by.full_name,
                "is_open": quick_assignment.is_open,
                "learner": learner
                and {"full_name": learner.full_name, "is_signed_in": is_signed_in},
                "is_coach": self.is_coach(request, quick_assignment),
            }
        )

    @action(detail=True, methods=["post"])
    def join(self, request, pk):
        quick_assignment = self.get_quick_assignment(pk)
        if self.is_coach(request, quick_assignment):
            raise PermissionDenied("Coaches see learners' work in Coach")
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        full_name = serializer.validated_data.get("full_name", "").strip()
        lesson = quick_assignment.lesson
        browser_key = None
        if full_name:
            if not quick_assignment.is_open:
                raise PermissionDenied("This assignment is not taking new learners")
            with transaction.atomic():
                learner = FacilityUser.objects.create_user(
                    _username_for(full_name),
                    password=NOT_SPECIFIED,
                    facility=Facility.objects.get(dataset_id=lesson.dataset_id),
                    full_name=full_name,
                )
                browser_key = secrets.token_urlsafe(32)
                LinkLearner.objects.create(
                    user=learner, key_hash=_key_hash(browser_key)
                )
                self.add_to(quick_assignment, learner)
        else:
            learner, _ = self.current_learner(request, quick_assignment)
            if learner is None:
                raise ValidationError({"full_name": "Give your full name"})
            joined = quick_assignment.group.get_members().filter(pk=learner.pk).exists()
            if not joined and not quick_assignment.is_open:
                raise PermissionDenied("This assignment is not taking new learners")
            self.add_to(quick_assignment, learner)
        if request.user != learner:
            logout(request)
            login(request, learner)
        response = Response(self.where_to_go(quick_assignment))
        if browser_key:
            response.set_cookie(
                BROWSER_KEY_COOKIE,
                f"{learner.id}.{browser_key}",
                max_age=BROWSER_KEY_MAX_AGE,
                path=settings.SESSION_COOKIE_PATH,
                secure=request.is_secure(),
                httponly=True,
                samesite="Lax",
            )
        return response

    def add_to(self, quick_assignment, learner):
        quick_assignment.lesson.collection.add_member(learner)
        quick_assignment.group.add_member(learner)

    def where_to_go(self, quick_assignment):
        lesson = quick_assignment.lesson
        web_page_id = (
            LessonWebPage.objects.filter(lesson=lesson)
            .values_list("id", flat=True)
            .first()
        )
        resources = lesson.resources
        return {
            "classroom_id": lesson.collection_id,
            "lesson_id": lesson.id,
            "web_page_id": web_page_id,
            # Straight to the exercise, when there is just one
            "contentnode_id": resources[0]["contentnode_id"]
            if not web_page_id and len(resources) == 1
            else None,
        }
