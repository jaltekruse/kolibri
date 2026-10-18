import base64
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
from kolibri.plugins.lesson_responses.utils import MAX_ANSWER_LENGTH

DUMMY_PASSWORD = "password"
BASENAME = "kolibri:kolibri.plugins.lesson_responses:lessonresponse"


def doc(text):
    """Stands in for a base64 encoded Free Math document"""
    return base64.b64encode(text.encode()).decode()


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

    def _grade(self, grades, resource=None):
        return self.client.post(
            reverse(BASENAME + "-grade"),
            {
                "lesson_id": self.lesson.id,
                "contentnode_id": (resource or self.resource)["contentnode_id"],
                "grades": grades,
            },
            format="json",
        )

    def _documents(self, rows):
        return {row["item"]: row["answer"]["free_math"] for row in rows}

    def test_save_draft_answers(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: doc("My first answer")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._documents(response.data), {self.prompt_ids[0]: doc("My first answer")}
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
        self._save({self.prompt_ids[0]: doc("Draft")})
        response = self._save({self.prompt_ids[0]: doc("Revised")})
        self.assertEqual(
            self._documents(response.data), {self.prompt_ids[0]: doc("Revised")}
        )
        self.assertEqual(AttemptLog.objects.filter(user=self.learner).count(), 1)

    def test_blank_answer_to_unanswered_prompt_is_not_stored(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_answer_can_be_cleared(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Draft")})
        response = self._save({self.prompt_ids[0]: ""})
        self.assertEqual(self._documents(response.data), {self.prompt_ids[0]: ""})

    def test_submit_marks_answers_complete(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Answer one")})
        response = self._save({self.prompt_ids[1]: doc("Answer two")}, submit=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._documents(response.data),
            {
                self.prompt_ids[0]: doc("Answer one"),
                self.prompt_ids[1]: doc("Answer two"),
            },
        )
        self.assertTrue(all(row["complete"] for row in response.data))
        self.assertEqual(ContentSummaryLog.objects.get(user=self.learner).progress, 1)
        self.assertTrue(MasteryLog.objects.get(user=self.learner).complete)

    def test_cannot_save_after_submit(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Final")}, submit=True)
        response = self._save({self.prompt_ids[0]: doc("Changed my mind")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            AttemptLog.objects.get(user=self.learner).answer,
            {"free_math": doc("Final")},
        )

    def test_unknown_prompt_rejected(self):
        self._login(self.learner)
        response = self._save({uuid.uuid4().hex: doc("Answer")})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttemptLog.objects.exists())

    def test_resource_without_prompts_rejected(self):
        self._login(self.learner)
        response = self._save(
            {self.prompt_ids[0]: doc("Answer")}, resource=self.resource_without_prompts
        )
        self.assertEqual(response.status_code, 400)

    def test_answer_too_long_rejected(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: "a" * (MAX_ANSWER_LENGTH + 4)})
        self.assertEqual(response.status_code, 400)

    def test_answer_that_is_not_base64_rejected(self):
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: "Plain text"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttemptLog.objects.exists())

    def test_unassigned_lesson_not_found(self):
        lesson = self._create_lesson("Unassigned", [self.resource], assigned=False)
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: doc("Answer")}, lesson=lesson)
        self.assertEqual(response.status_code, 404)

    def test_inactive_lesson_not_found(self):
        lesson = self._create_lesson("Inactive", [self.resource], is_active=False)
        self._login(self.learner)
        response = self._save({self.prompt_ids[0]: doc("Answer")}, lesson=lesson)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_cannot_save(self):
        response = self._save({self.prompt_ids[0]: doc("Answer")})
        self.assertEqual(response.status_code, 403)

    def test_same_resource_in_two_lessons_keeps_separate_answers(self):
        other_lesson = self._create_lesson("Other lesson", [self.resource])
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Lesson one answer")}, submit=True)
        response = self._save(
            {self.prompt_ids[0]: doc("Lesson two answer")}, lesson=other_lesson
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._documents(self._list().data),
            {self.prompt_ids[0]: doc("Lesson one answer")},
        )
        self.assertEqual(
            self._documents(self._list(lesson=other_lesson).data),
            {self.prompt_ids[0]: doc("Lesson two answer")},
        )

    def test_learner_lists_only_own_answers(self):
        self._login(self.other_learner)
        self._save({self.prompt_ids[0]: doc("Other learner's answer")})
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("My answer")})
        response = self._list()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(row["user"], row["answer"]["free_math"]) for row in response.data],
            [(self.learner.id, doc("My answer"))],
        )

    def test_coach_lists_all_learner_answers(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Learner answer")})
        self._login(self.other_learner)
        self._save({self.prompt_ids[1]: doc("Other learner answer")}, submit=True)
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

    def test_coach_grades_learner_answers(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Answer one")}, submit=True)
        self._login(self.coach)
        response = self._grade(
            {self.learner.id: {self.prompt_ids[0]: doc("Answer one, 5/6 points")}}
        )
        self.assertEqual(response.status_code, 204)
        self._login(self.learner)
        self.assertEqual(
            self._documents(self._list().data),
            {self.prompt_ids[0]: doc("Answer one, 5/6 points")},
        )

    def test_coach_grades_answers_before_they_are_submitted(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Draft")})
        self._login(self.coach)
        response = self._grade(
            {self.learner.id: {self.prompt_ids[0]: doc("Draft, keep going")}}
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AttemptLog.objects.get(user=self.learner).complete)

    def test_unsaved_answer_cannot_be_graded(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Answer one")})
        self._login(self.coach)
        response = self._grade(
            {self.learner.id: {self.prompt_ids[1]: doc("Graded answer two")}}
        )
        self.assertEqual(response.status_code, 400)

    def test_grading_unknown_prompt_rejected(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Answer one")})
        self._login(self.coach)
        response = self._grade({self.learner.id: {uuid.uuid4().hex: doc("Graded")}})
        self.assertEqual(response.status_code, 400)

    def test_learner_cannot_grade_own_answers(self):
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Final")}, submit=True)
        response = self._grade({self.learner.id: {self.prompt_ids[0]: doc("Changed")}})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            AttemptLog.objects.get(user=self.learner).answer,
            {"free_math": doc("Final")},
        )

    def test_coach_of_another_class_cannot_grade(self):
        other_classroom = Classroom.objects.create(name="Other", parent=self.facility)
        other_coach = self._create_user("other_coach")
        other_classroom.add_coach(other_coach)
        self._login(self.learner)
        self._save({self.prompt_ids[0]: doc("Answer one")})
        self._login(other_coach)
        response = self._grade({self.learner.id: {self.prompt_ids[0]: doc("Graded")}})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            AttemptLog.objects.get(user=self.learner).answer,
            {"free_math": doc("Answer one")},
        )
