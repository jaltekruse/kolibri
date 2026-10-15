import uuid

from django.urls import reverse

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.auth.test.helpers import clear_process_cache
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.auth.utils.delete import delete_facility
from kolibri.core.lessons.models import Lesson
from kolibri.core.lessons.models import LessonAssignment
from kolibri.plugins.lesson_responses.models import LessonResponseFeedback

DUMMY_PASSWORD = "password"
BASENAME = "kolibri:kolibri.plugins.lesson_responses:lessonresponsefeedback"


class LessonResponseFeedbackTestCase(APITestCase):
    databases = "__all__"

    def setUp(self):
        clear_process_cache()
        provision_device()
        self.facility = Facility.objects.create(name="MyFac")
        self.classroom = Classroom.objects.create(name="Class", parent=self.facility)
        self.coach = self._create_user("coach")
        self.classroom.add_coach(self.coach)
        self.learner = self._create_user("learner")
        self.other_learner = self._create_user("other_learner")
        self.classroom.add_member(self.learner)
        self.classroom.add_member(self.other_learner)

        self.prompt_id = uuid.uuid4().hex
        self.resource = {
            "contentnode_id": uuid.uuid4().hex,
            "content_id": uuid.uuid4().hex,
            "channel_id": uuid.uuid4().hex,
            "prompts": [{"id": self.prompt_id, "text": "Answer question 1"}],
        }
        self.lesson = Lesson.objects.create(
            title="Lesson",
            collection=self.classroom,
            created_by=self.coach,
            is_active=True,
            resources=[self.resource],
        )
        LessonAssignment.objects.create(
            lesson=self.lesson, assigned_by=self.coach, collection=self.classroom
        )

    def _create_user(self, username):
        user = FacilityUser.objects.create(username=username, facility=self.facility)
        user.set_password(DUMMY_PASSWORD)
        user.save()
        return user

    def _login(self, user):
        self.client.login(username=user.username, password=DUMMY_PASSWORD)

    def _create(self, learner=None, **data):
        return self.client.post(
            reverse(BASENAME + "-list"),
            {
                "user": (learner or self.learner).id,
                "lesson_id": self.lesson.id,
                "contentnode_id": self.resource["contentnode_id"],
                "comment": "Good work",
                "prompt_comments": {self.prompt_id: "Check page 3 again"},
                **data,
            },
            format="json",
        )

    def _list(self):
        return self.client.get(
            reverse(BASENAME + "-list"),
            {
                "lesson_id": self.lesson.id,
                "contentnode_id": self.resource["contentnode_id"],
            },
        )

    def test_coach_creates_feedback(self):
        self._login(self.coach)
        response = self._create()
        self.assertEqual(response.status_code, 201)
        feedback = LessonResponseFeedback.objects.get(user=self.learner)
        self.assertEqual(feedback.comment, "Good work")
        self.assertEqual(
            feedback.prompt_comments, {self.prompt_id: "Check page 3 again"}
        )

    def test_feedback_syncs_only_to_its_learner(self):
        self._login(self.coach)
        self._create()
        feedback = LessonResponseFeedback.objects.get(user=self.learner)
        self.assertEqual(
            feedback.calculate_partition(),
            f"{self.facility.dataset_id}:user-ro:{self.learner.id}",
        )

    def test_coach_updates_feedback(self):
        self._login(self.coach)
        feedback_id = self._create().data["id"]
        response = self.client.patch(
            reverse(BASENAME + "-detail", kwargs={"pk": feedback_id}),
            {"comment": "Great revision"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LessonResponseFeedback.objects.get(id=feedback_id).comment,
            "Great revision",
        )

    def test_feedback_deleted_with_facility(self):
        self._login(self.coach)
        self._create()
        delete_facility(self.facility)
        self.assertFalse(LessonResponseFeedback.objects.exists())

    def test_learner_reads_only_own_feedback(self):
        self._login(self.coach)
        self._create()
        self._create(learner=self.other_learner, comment="For someone else")
        self._login(self.learner)
        response = self._list()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(row["user"], row["comment"]) for row in response.data],
            [(self.learner.id, "Good work")],
        )

    def test_learner_cannot_create_feedback(self):
        self._login(self.learner)
        response = self._create()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonResponseFeedback.objects.exists())

    def test_learner_cannot_update_feedback(self):
        self._login(self.coach)
        feedback_id = self._create().data["id"]
        self._login(self.learner)
        response = self.client.patch(
            reverse(BASENAME + "-detail", kwargs={"pk": feedback_id}),
            {"comment": "Changed by learner"},
            format="json",
        )
        self.assertIn(response.status_code, (403, 404))
        self.assertEqual(
            LessonResponseFeedback.objects.get(id=feedback_id).comment, "Good work"
        )

    def test_coach_of_other_class_cannot_create_feedback(self):
        other_classroom = Classroom.objects.create(name="Other", parent=self.facility)
        other_coach = self._create_user("other_coach")
        other_classroom.add_coach(other_coach)
        self._login(other_coach)
        response = self._create()
        self.assertEqual(response.status_code, 403)

    def test_comment_on_unknown_prompt_rejected(self):
        self._login(self.coach)
        response = self._create(prompt_comments={uuid.uuid4().hex: "Comment"})
        self.assertEqual(response.status_code, 400)

    def test_feedback_for_resource_without_prompts_rejected(self):
        self._login(self.coach)
        response = self._create(contentnode_id=uuid.uuid4().hex)
        self.assertEqual(response.status_code, 400)

    def test_list_requires_lesson_and_resource(self):
        self._login(self.coach)
        response = self.client.get(
            reverse(BASENAME + "-list"), {"lesson_id": self.lesson.id}
        )
        self.assertEqual(response.status_code, 400)
