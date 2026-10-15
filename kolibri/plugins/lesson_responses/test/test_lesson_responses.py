import uuid

from django.urls import reverse

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.auth.test.helpers import clear_process_cache
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.lessons.models import Lesson
from kolibri.core.lessons.models import LessonAssignment
from kolibri.core.logger.models import AttemptLog
from kolibri.core.logger.models import ContentSummaryLog
from kolibri.core.logger.models import MasteryLog
from kolibri.plugins.lesson_responses.utils import get_response_content_id

DUMMY_PASSWORD = "password"
BASENAME = "kolibri:kolibri.plugins.lesson_responses:lessonresponse"


class LessonResponsesTestCase(APITestCase):
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

        self.prompt_ids = [uuid.uuid4().hex, uuid.uuid4().hex]
        self.resource = {
            "contentnode_id": uuid.uuid4().hex,
            "content_id": uuid.uuid4().hex,
            "channel_id": uuid.uuid4().hex,
            "prompts": [
                {"id": self.prompt_ids[0], "text": "Answer question 1 on page 2"},
                {"id": self.prompt_ids[1], "text": "Summarize the second section"},
            ],
        }
        self.resource_without_prompts = {
            "contentnode_id": uuid.uuid4().hex,
            "content_id": uuid.uuid4().hex,
            "channel_id": uuid.uuid4().hex,
        }
        self.lesson = self._create_lesson(
            "Lesson", [self.resource, self.resource_without_prompts]
        )

    def _create_user(self, username):
        user = FacilityUser.objects.create(username=username, facility=self.facility)
        user.set_password(DUMMY_PASSWORD)
        user.save()
        return user

    def _create_lesson(self, title, resources, is_active=True, assigned=True):
        lesson = Lesson.objects.create(
            title=title,
            collection=self.classroom,
            created_by=self.coach,
            is_active=is_active,
            resources=resources,
        )
        if assigned:
            LessonAssignment.objects.create(
                lesson=lesson, assigned_by=self.coach, collection=self.classroom
            )
        return lesson

    def _login(self, user):
        self.client.login(username=user.username, password=DUMMY_PASSWORD)

    def _save(self, answers, submit=False, lesson=None, resource=None):
        return self.client.post(
            reverse(BASENAME + "-save"),
            {
                "lesson_id": (lesson or self.lesson).id,
                "contentnode_id": (resource or self.resource)["contentnode_id"],
                "answers": answers,
                "submit": submit,
            },
            format="json",
        )

    def _list(self, lesson=None):
        return self.client.get(
            reverse(BASENAME + "-list"),
            {
                "lesson_id": (lesson or self.lesson).id,
                "contentnode_id": self.resource["contentnode_id"],
            },
        )

    def _texts(self, rows):
        return {row["item"]: row["answer"]["text"] for row in rows}

    def test_save_draft_answers(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: "My first answer"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._texts(response.data), {self.prompt_ids[0]: "My first answer"}
        )
        self.assertFalse(response.data[0]["complete"])
        summarylog = ContentSummaryLog.objects.get(user=self.learner)
        self.assertEqual(
            summarylog.content_id,
            get_response_content_id(self.lesson.id, self.resource["contentnode_id"]),
        )
        self.assertEqual(summarylog.progress, 0)

    def test_save_updates_existing_answer(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "Draft"})
        response = self._save({self.prompt_ids[0]: "Revised"})
        self.assertEqual(self._texts(response.data), {self.prompt_ids[0]: "Revised"})
        self.assertEqual(AttemptLog.objects.filter(user=self.learner).count(), 1)

    def test_blank_answer_to_unanswered_prompt_is_not_stored(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_answer_can_be_cleared(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "Draft"})
        response = self._save({self.prompt_ids[0]: ""})
        self.assertEqual(self._texts(response.data), {self.prompt_ids[0]: ""})

    def test_submit_marks_answers_complete(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "Answer one"})
        response = self._save({self.prompt_ids[1]: "Answer two"}, submit=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._texts(response.data),
            {self.prompt_ids[0]: "Answer one", self.prompt_ids[1]: "Answer two"},
        )
        self.assertTrue(all(row["complete"] for row in response.data))
        self.assertEqual(ContentSummaryLog.objects.get(user=self.learner).progress, 1)
        self.assertTrue(MasteryLog.objects.get(user=self.learner).complete)

    def test_cannot_save_after_submit(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "Final"}, submit=True)
        response = self._save({self.prompt_ids[0]: "Changed my mind"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            AttemptLog.objects.get(user=self.learner).answer, {"text": "Final"}
        )

    def test_unknown_prompt_rejected(self):
        self._login(self.learner)
        response = self._save({uuid.uuid4().hex: "Answer"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttemptLog.objects.exists())

    def test_resource_without_prompts_rejected(self):
        self._login(self.learner)
        response = self._save(
            {self.prompt_ids[0]: "Answer"}, resource=self.resource_without_prompts
        )
        self.assertEqual(response.status_code, 400)

    def test_answer_too_long_rejected(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: "a" * 10001})
        self.assertEqual(response.status_code, 400)

    def test_unassigned_lesson_not_found(self):
        lesson = self._create_lesson("Unassigned", [self.resource], assigned=False)
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: "Answer"}, lesson=lesson)
        self.assertEqual(response.status_code, 404)

    def test_inactive_lesson_not_found(self):
        lesson = self._create_lesson("Inactive", [self.resource], is_active=False)
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: "Answer"}, lesson=lesson)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_cannot_save(self):
        response = self._save({self.prompt_ids[0]: "Answer"})
        self.assertEqual(response.status_code, 403)

    def test_same_resource_in_two_lessons_keeps_separate_answers(self):
        other_lesson = self._create_lesson("Other lesson", [self.resource])
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "Lesson one answer"}, submit=True)
        response = self._save(
            {self.prompt_ids[0]: "Lesson two answer"}, lesson=other_lesson
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._texts(self._list().data), {self.prompt_ids[0]: "Lesson one answer"}
        )
        self.assertEqual(
            self._texts(self._list(lesson=other_lesson).data),
            {self.prompt_ids[0]: "Lesson two answer"},
        )

    def test_learner_lists_only_own_answers(self):
        self._login(self.other_learner)
        self._save({self.prompt_ids[0]: "Other learner's answer"})
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "My answer"})
        response = self._list()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(row["user"], row["answer"]["text"]) for row in response.data],
            [(self.learner.id, "My answer")],
        )

    def test_coach_lists_all_learner_answers(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: "Learner answer"})
        self._login(self.other_learner)
        self._save({self.prompt_ids[1]: "Other learner answer"}, submit=True)
        self._login(self.coach)
        response = self._list()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(
                (row["user"], row["item"], row["complete"]) for row in response.data
            ),
            sorted(
                [
                    (self.learner.id, self.prompt_ids[0], False),
                    (self.other_learner.id, self.prompt_ids[1], True),
                ]
            ),
        )

    def test_list_requires_lesson_and_resource(self):
        self._login(self.coach)
        response = self.client.get(
            reverse(BASENAME + "-list"), {"lesson_id": self.lesson.id}
        )
        self.assertEqual(response.status_code, 400)
