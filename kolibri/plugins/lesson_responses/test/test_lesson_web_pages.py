import base64

import pytest
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
from kolibri.core.logger.models import AttemptLog
from kolibri.core.logger.models import ContentSessionLog
from kolibri.plugins.lesson_responses.models import LessonWebPage
from kolibri.plugins.lesson_responses.utils import expand_problem_numbers
from kolibri.plugins.lesson_responses.utils import MAX_PROBLEMS

DUMMY_PASSWORD = "password"
WEB_PAGES = "kolibri:kolibri.plugins.lesson_responses:lessonwebpage"
RESPONSES = "kolibri:kolibri.plugins.lesson_responses:lessonresponse"


def doc(text):
    """Stands in for a base64 encoded Free Math document"""
    return base64.b64encode(text.encode()).decode()


def test_expand_ranges_with_steps():
    assert expand_problem_numbers("1-5, 21-35 by 3s") == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "21",
        "24",
        "27",
        "30",
        "33",
    ]


def test_expand_other_separators_and_range_forms():
    assert expand_problem_numbers("2 to 4; 10-14/2 and 7") == [
        "2",
        "3",
        "4",
        "10",
        "12",
        "14",
        "7",
    ]


def test_expand_keeps_problem_labels_once():
    assert expand_problem_numbers("4a, Review  2, 4a, 5") == ["4a", "Review 2", "5"]


@pytest.mark.parametrize(
    "problem_numbers",
    ["10-1", "1-5 by 0", "", " , ", f"1-{MAX_PROBLEMS + 1}", "1-100000000000"],
)
def test_expand_rejects_unusable_lists(problem_numbers):
    with pytest.raises(ValueError):
        expand_problem_numbers(problem_numbers)


class LessonWebPagesTestCase(APITestCase):
    databases = "__all__"

    def setUp(self):
        clear_process_cache()
        provision_device()
        self.facility = Facility.objects.create(name="MyFac")
        self.classroom = Classroom.objects.create(name="Class", parent=self.facility)
        self.coach = self._create_user("coach")
        self.classroom.add_coach(self.coach)
        self.learner = self._create_user("learner")
        self.classroom.add_member(self.learner)
        self.lesson = self._create_lesson("Equations")

    def _create_user(self, username):
        user = FacilityUser.objects.create(username=username, facility=self.facility)
        user.set_password(DUMMY_PASSWORD)
        user.save()
        return user

    def _create_lesson(self, title, is_active=True, assigned=True):
        lesson = Lesson.objects.create(
            title=title,
            collection=self.classroom,
            created_by=self.coach,
            is_active=is_active,
            resources=[],
        )
        if assigned:
            LessonAssignment.objects.create(
                lesson=lesson, assigned_by=self.coach, collection=self.classroom
            )
        return lesson

    def _create_web_page(self, lesson=None, problem_numbers="1-3, 10-20 by 5"):
        return LessonWebPage.objects.create(
            lesson=lesson or self.lesson,
            title="Two-step equations",
            url="https://example.org/equations",
            instructions="Solve the odd problems",
            problem_numbers=problem_numbers,
        )

    def _login(self, user):
        self.client.login(username=user.username, password=DUMMY_PASSWORD)

    def _post_web_page(self, **data):
        return self.client.post(
            reverse(WEB_PAGES + "-list"),
            {
                "lesson": self.lesson.id,
                "title": "Two-step equations",
                "url": "https://example.org/equations",
                "instructions": "Solve problems 1-3",
                "problem_numbers": "1-3",
                **data,
            },
            format="json",
        )

    def _list(self, lesson=None):
        return self.client.get(
            reverse(WEB_PAGES + "-list"), {"lesson": (lesson or self.lesson).id}
        )

    def test_coach_adds_web_page_to_lesson(self):
        self._login(self.coach)
        response = self._post_web_page(problem_numbers="1-3, 21-35 by 3s")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["problems"],
            ["1", "2", "3", "21", "24", "27", "30", "33"],
        )
        web_page = LessonWebPage.objects.get(id=response.data["id"])
        self.assertEqual(web_page.lesson_id, self.lesson.id)
        self.assertEqual(web_page.url, "https://example.org/equations")

    def test_unusable_problem_numbers_rejected(self):
        self._login(self.coach)
        response = self._post_web_page(problem_numbers="20-1")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LessonWebPage.objects.exists())

    def test_only_web_addresses_accepted(self):
        self._login(self.coach)
        for url in ("javascript:alert(1)", "ftp://example.org/file", "example"):
            response = self._post_web_page(url=url)
            self.assertEqual(response.status_code, 400, url)
        self.assertFalse(LessonWebPage.objects.exists())

    def test_coach_of_another_class_cannot_add_web_page(self):
        other_classroom = Classroom.objects.create(name="Other", parent=self.facility)
        other_coach = self._create_user("other_coach")
        other_classroom.add_coach(other_coach)
        self._login(other_coach)
        response = self._post_web_page()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonWebPage.objects.exists())

    def test_learner_cannot_add_web_page(self):
        self._login(self.learner)
        response = self._post_web_page()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonWebPage.objects.exists())

    def test_coach_edits_web_page_but_not_its_lesson(self):
        web_page = self._create_web_page()
        other_lesson = self._create_lesson("Inequalities")
        self._login(self.coach)
        response = self.client.patch(
            reverse(WEB_PAGES + "-detail", kwargs={"pk": web_page.id}),
            {"problem_numbers": "4-6", "lesson": other_lesson.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["problems"], ["4", "5", "6"])
        web_page.refresh_from_db()
        self.assertEqual(web_page.lesson_id, self.lesson.id)

    def test_learner_cannot_delete_web_page(self):
        web_page = self._create_web_page()
        self._login(self.learner)
        response = self.client.delete(
            reverse(WEB_PAGES + "-detail", kwargs={"pk": web_page.id})
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(LessonWebPage.objects.exists())

    def test_coach_deletes_web_page(self):
        web_page = self._create_web_page()
        self._login(self.coach)
        response = self.client.delete(
            reverse(WEB_PAGES + "-detail", kwargs={"pk": web_page.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(LessonWebPage.objects.exists())

    def test_web_pages_deleted_with_their_lesson(self):
        self._create_web_page()
        self.lesson.delete()
        self.assertFalse(LessonWebPage.objects.exists())

    @override_settings(DEBUG=True)
    def test_learner_lists_web_pages_of_assigned_active_lessons(self):
        web_page = self._create_web_page()
        self._create_web_page(lesson=self._create_lesson("Draft", is_active=False))
        self._create_web_page(lesson=self._create_lesson("Unassigned", assigned=False))
        self._login(self.learner)
        response = self.client.get(reverse(WEB_PAGES + "-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [web_page.id])
        self.assertEqual(
            response.data[0]["problems"], ["1", "2", "3", "10", "15", "20"]
        )

    def test_coach_lists_web_pages_by_lesson(self):
        web_page = self._create_web_page()
        draft = self._create_lesson("Draft", is_active=False)
        draft_web_page = self._create_web_page(lesson=draft)
        self._login(self.coach)
        self.assertEqual([row["id"] for row in self._list().data], [web_page.id])
        self.assertEqual(
            [row["id"] for row in self._list(lesson=draft).data], [draft_web_page.id]
        )

    def test_learner_answers_and_coach_grades_web_page_problems(self):
        web_page = self._create_web_page()
        self._login(self.learner)
        response = self.client.post(
            reverse(RESPONSES + "-save"),
            {
                "lesson_id": self.lesson.id,
                "item_id": web_page.id,
                "answers": {"15": doc("x = 3")},
                "submit": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ContentSessionLog.objects.get(user=self.learner).extra_fields["context"],
            {"lesson_id": self.lesson.id, "web_page_id": web_page.id},
        )
        self._login(self.coach)
        response = self.client.post(
            reverse(RESPONSES + "-grade"),
            {
                "lesson_id": self.lesson.id,
                "item_id": web_page.id,
                "grades": {self.learner.id: {"15": doc("x = 3, 6/6")}},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            AttemptLog.objects.get(user=self.learner, item="15").answer,
            {"free_math": doc("x = 3, 6/6")},
        )

    def test_answers_must_be_for_listed_problems(self):
        web_page = self._create_web_page()
        self._login(self.learner)
        response = self.client.post(
            reverse(RESPONSES + "-save"),
            {
                "lesson_id": self.lesson.id,
                "item_id": web_page.id,
                "answers": {"4": doc("Not a listed problem")},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttemptLog.objects.exists())

    def test_web_page_in_another_lesson_rejected(self):
        web_page = self._create_web_page(lesson=self._create_lesson("Other"))
        self._login(self.learner)
        response = self.client.post(
            reverse(RESPONSES + "-save"),
            {
                "lesson_id": self.lesson.id,
                "item_id": web_page.id,
                "answers": {"1": doc("Answer")},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttemptLog.objects.exists())
