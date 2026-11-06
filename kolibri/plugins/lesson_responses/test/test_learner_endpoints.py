import uuid

from django.test import override_settings
from django.urls import reverse

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.auth.test.helpers import clear_process_cache
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.lessons.models import Lesson
from kolibri.core.lessons.models import LessonAssignment


# DEBUG checks API output against the serializers' declared fields, so these tests
# catch lesson endpoints that do not allow for prompts on lesson resources.
@override_settings(DEBUG=True)
class LearnerLessonEndpointsWithPromptsTestCase(APITestCase):
    databases = "__all__"

    def setUp(self):
        clear_process_cache()
        provision_device()
        self.facility = Facility.objects.create(name="MyFac")
        self.classroom = Classroom.objects.create(name="Class", parent=self.facility)
        self.learner = FacilityUser.objects.create(
            username="learner", facility=self.facility
        )
        self.learner.set_password("password")
        self.learner.save()
        self.classroom.add_member(self.learner)
        self.prompts = [{"id": uuid.uuid4().hex, "text": "Answer question 1"}]
        self.lesson = Lesson.objects.create(
            title="Lesson",
            collection=self.classroom,
            created_by=self.learner,
            is_active=True,
            resources=[
                {
                    "contentnode_id": uuid.uuid4().hex,
                    "content_id": uuid.uuid4().hex,
                    "channel_id": uuid.uuid4().hex,
                    "prompts": self.prompts,
                }
            ],
        )
        LessonAssignment.objects.create(
            lesson=self.lesson, assigned_by=self.learner, collection=self.classroom
        )
        self.client.login(username="learner", password="password")

    def test_learner_classroom_includes_prompts(self):
        response = self.client.get(
            reverse("kolibri:kolibri.plugins.learn:learnerclassroom-list")
        )
        self.assertEqual(response.status_code, 200)
        lesson = response.data[0]["lessons"][0]
        self.assertEqual(lesson["resources"][0]["prompts"], self.prompts)

    def test_learner_lesson_includes_prompts(self):
        response = self.client.get(
            reverse(
                "kolibri:kolibri.plugins.learn:learnerlesson-detail",
                kwargs={"pk": self.lesson.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["resources"][0]["prompts"], self.prompts)
