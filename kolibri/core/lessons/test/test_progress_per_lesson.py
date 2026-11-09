import uuid

from django.urls import reverse
from le_utils.constants import content_kinds

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.test.helpers import DUMMY_PASSWORD
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.auth.test.test_api import FacilityFactory
from kolibri.core.auth.test.test_api import FacilityUserFactory
from kolibri.core.content.models import ContentNode
from kolibri.core.lessons.models import Lesson
from kolibri.core.lessons.models import LessonAssignment
from kolibri.core.lessons.utils import lesson_content_id
from kolibri.core.logger.models import ContentSummaryLog


class ProgressPerLessonTestCase(APITestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        provision_device()
        cls.facility = FacilityFactory.create()
        cls.classroom = Classroom.objects.create(name="Class", parent=cls.facility)
        cls.learner = FacilityUserFactory(facility=cls.facility)
        cls.classroom.add_member(cls.learner)
        cls.coach = FacilityUserFactory(facility=cls.facility)
        cls.classroom.add_coach(cls.coach)
        cls.channel_id = uuid.uuid4().hex
        cls.per_lesson_node = cls.create_node({"progress_per_lesson": True})
        cls.other_node = cls.create_node({})

    @classmethod
    def create_node(cls, options):
        return ContentNode.objects.create(
            id=uuid.uuid4().hex,
            content_id=uuid.uuid4().hex,
            channel_id=cls.channel_id,
            kind=content_kinds.HTML5,
            title="Resource",
            options=options,
        )

    def create_lesson(self):
        lesson = Lesson.objects.create(
            title="Lesson",
            collection=self.classroom,
            created_by=self.coach,
            is_active=True,
            resources=[
                {
                    "contentnode_id": node.id,
                    "content_id": node.content_id,
                    "channel_id": node.channel_id,
                }
                for node in (self.per_lesson_node, self.other_node)
            ],
        )
        LessonAssignment.objects.create(
            lesson=lesson, collection=self.classroom, assigned_by=self.coach
        )
        return lesson

    def resource_content_ids(self, lesson):
        return {r["contentnode_id"]: r["content_id"] for r in lesson.resources}

    def start_session(self, node, lesson=None):
        data = {
            "node_id": node.id,
            "content_id": node.content_id,
            "channel_id": node.channel_id,
            "kind": node.kind,
        }
        if lesson:
            data["lesson_id"] = lesson.id
        response = self.client.post(
            reverse("kolibri:core:trackprogress-list"), data=data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_lesson_gives_resource_its_own_content_id(self):
        lesson = self.create_lesson()
        lesson.refresh_from_db()
        self.assertEqual(
            self.resource_content_ids(lesson),
            {
                self.per_lesson_node.id: lesson_content_id(
                    lesson.id, self.per_lesson_node.content_id
                ),
                self.other_node.id: self.other_node.content_id,
            },
        )

    def test_progress_kept_separately_for_each_lesson(self):
        lesson = self.create_lesson()
        other_lesson = self.create_lesson()
        self.client.login(
            username=self.learner.username,
            password=DUMMY_PASSWORD,
            facility=self.facility,
        )
        self.start_session(self.per_lesson_node, lesson)
        self.start_session(self.per_lesson_node, other_lesson)
        self.start_session(self.per_lesson_node)
        self.assertEqual(
            set(
                ContentSummaryLog.objects.filter(user=self.learner).values_list(
                    "content_id", flat=True
                )
            ),
            {
                self.resource_content_ids(lesson)[self.per_lesson_node.id],
                self.resource_content_ids(other_lesson)[self.per_lesson_node.id],
                self.per_lesson_node.content_id,
            },
        )

    def test_other_resources_keep_one_progress_across_lessons(self):
        lesson = self.create_lesson()
        other_lesson = self.create_lesson()
        self.client.login(
            username=self.learner.username,
            password=DUMMY_PASSWORD,
            facility=self.facility,
        )
        self.start_session(self.other_node, lesson)
        self.start_session(self.other_node, other_lesson)
        self.assertEqual(
            list(
                ContentSummaryLog.objects.filter(user=self.learner).values_list(
                    "content_id", flat=True
                )
            ),
            [self.other_node.content_id],
        )

    def test_learner_lesson_shows_progress_in_that_lesson(self):
        lesson = self.create_lesson()
        other_lesson = self.create_lesson()
        ContentSummaryLog.objects.create(
            user=self.learner,
            content_id=self.resource_content_ids(lesson)[self.per_lesson_node.id],
            channel_id=self.channel_id,
            kind=content_kinds.HTML5,
            progress=0.5,
            start_timestamp=lesson.date_created,
        )
        self.client.login(
            username=self.learner.username,
            password=DUMMY_PASSWORD,
            facility=self.facility,
        )
        progress = {}
        for each in (lesson, other_lesson):
            response = self.client.get(
                reverse(
                    "kolibri:kolibri.plugins.learn:learnerlesson-detail",
                    kwargs={"pk": each.id},
                )
            )
            progress[each.id] = {
                r["contentnode_id"]: r["progress"] for r in response.data["resources"]
            }
        self.assertEqual(progress[lesson.id][self.per_lesson_node.id], 0.5)
        self.assertEqual(progress[other_lesson.id][self.per_lesson_node.id], 0)
