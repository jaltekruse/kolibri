from django.conf import settings
from django.urls import reverse
from le_utils.constants import content_kinds

from kolibri.core.auth.constants import role_kinds
from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.auth.test.helpers import clear_process_cache
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.lessons.models import Lesson
from kolibri.core.logger.models import AttemptLog
from kolibri.plugins.lesson_responses.models import LessonWebPage
from kolibri.plugins.quick_assign.models import QuickAssignment
from kolibri.plugins.quick_assign.root_urls import JOIN_LINK_URL_NAME
from kolibri.plugins.quick_assign.viewsets import BROWSER_KEY_COOKIE

PASSWORD = "password"
QUICK_ASSIGNMENTS = "kolibri:kolibri.plugins.quick_assign:quickassignment"
CLASS_NAME = "Ms. Rivera's quick assignments"
CHANNEL_ID = "a" * 32
EXERCISE_ID = "b" * 32
VIDEO_ID = "c" * 32
WEB_PAGE = {
    "url": "https://example.org/equations",
    "instructions": "Solve the odd problems",
    "problem_numbers": "1-5 by 2",
}


def content_node(node_id, kind, parent_id, lft):
    return ContentNode.objects.create(
        id=node_id,
        channel_id=CHANNEL_ID,
        parent_id=parent_id,
        content_id=node_id,
        title=f"{kind} {node_id[:4]}",
        kind=kind,
        available=True,
        tree_id=1,
        level=0 if parent_id is None else 1,
        lft=lft,
        rght=lft + 1,
    )


def link_url(token):
    return reverse("kolibri:kolibri.plugins.quick_assign:joinlink-detail", args=[token])


def join_url(token):
    return reverse("kolibri:kolibri.plugins.quick_assign:joinlink-join", args=[token])


class QuickAssignTestCase(APITestCase):
    databases = "__all__"

    def setUp(self):
        clear_process_cache()
        provision_device()
        self.facility = Facility.objects.create(name="School")
        self.coach = self.user("rivera", full_name="Ana Rivera")
        self.facility.add_role(self.coach, role_kinds.COACH)
        root = content_node(CHANNEL_ID, content_kinds.TOPIC, None, 1)
        ChannelMetadata.objects.create(
            id=CHANNEL_ID, name="Khan Academy", root=root, min_schema_version="1"
        )
        content_node(EXERCISE_ID, content_kinds.EXERCISE, root.id, 2)
        content_node(VIDEO_ID, content_kinds.VIDEO, root.id, 4)

    def user(self, username, full_name=""):
        user = FacilityUser.objects.create(
            username=username, full_name=full_name, facility=self.facility
        )
        user.set_password(PASSWORD)
        user.save()
        return user

    def sign_in(self, user):
        self.client.login(username=user.username, password=PASSWORD)

    def create(self, **data):
        data.setdefault("title", "Two-step equations")
        data.setdefault("classroom_name", CLASS_NAME)
        return self.client.post(
            reverse(f"{QUICK_ASSIGNMENTS}-list"), data, format="json"
        )

    def make_quick_assignment(self, **data):
        self.sign_in(self.coach)
        response = self.create(**data)
        self.assertEqual(response.status_code, 201, response.data)
        self.client.logout()
        return QuickAssignment.objects.get(lesson_id=response.data["id"])


class CreateQuickAssignmentTestCase(QuickAssignTestCase):
    def test_coaches_assign_an_exercise_from_the_library(self):
        self.sign_in(self.coach)

        response = self.create(exercise_ids=[EXERCISE_ID])

        self.assertEqual(response.status_code, 201, response.data)
        lesson = Lesson.objects.get(id=response.data["id"])
        self.assertEqual(lesson.title, "Two-step equations")
        self.assertTrue(lesson.is_active)
        self.assertEqual(
            [resource["contentnode_id"] for resource in lesson.resources], [EXERCISE_ID]
        )
        classroom = Classroom.objects.get(id=lesson.collection_id)
        self.assertEqual(classroom.name, CLASS_NAME)
        self.assertIn(self.coach, classroom.get_coaches())
        (assignment,) = lesson.lesson_assignments.all()
        self.assertEqual(assignment.collection.parent_id, classroom.id)
        self.assertEqual(response.data["token"], lesson.quick_assignment.token)

    def test_quick_assignments_share_the_coachs_class(self):
        self.sign_in(self.coach)
        first = self.create(exercise_ids=[EXERCISE_ID]).data
        second = self.create(web_page=WEB_PAGE, classroom_name="Ignored").data

        self.assertEqual(first["classroom_id"], second["classroom_id"])
        self.assertEqual(Classroom.objects.filter(parent=self.facility).count(), 1)
        self.assertNotEqual(first["token"], second["token"])

    def test_titles_stay_unique_in_the_class(self):
        self.sign_in(self.coach)
        self.create(exercise_ids=[EXERCISE_ID])

        response = self.create(exercise_ids=[EXERCISE_ID])

        self.assertEqual(response.data["title"], "Two-step equations (2)")

    def test_coaches_assign_free_math_work_on_a_web_page(self):
        self.sign_in(self.coach)

        response = self.create(web_page=WEB_PAGE)

        self.assertEqual(response.status_code, 201, response.data)
        (web_page,) = LessonWebPage.objects.filter(lesson_id=response.data["id"])
        self.assertEqual(web_page.title, "Two-step equations")
        self.assertEqual(web_page.url, WEB_PAGE["url"])
        self.assertEqual(web_page.problems, ["1", "3", "5"])
        self.assertEqual(response.data["web_page_id"], web_page.id)

    def test_needs_exercises_or_a_web_page(self):
        self.sign_in(self.coach)

        self.assertEqual(self.create().status_code, 400)
        both = self.create(exercise_ids=[EXERCISE_ID], web_page=WEB_PAGE)
        self.assertEqual(both.status_code, 400)
        self.assertFalse(Lesson.objects.exists())

    def test_only_assigns_exercises(self):
        self.sign_in(self.coach)

        self.assertEqual(self.create(exercise_ids=[VIDEO_ID]).status_code, 400)
        self.assertEqual(self.create(exercise_ids=["d" * 32]).status_code, 400)

    def test_checks_web_page_problem_numbers(self):
        self.sign_in(self.coach)

        response = self.create(web_page={**WEB_PAGE, "problem_numbers": "5-1"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Lesson.objects.exists())

    def test_learners_cannot_quick_assign(self):
        self.sign_in(self.user("learner"))

        self.assertEqual(self.create(exercise_ids=[EXERCISE_ID]).status_code, 403)


class ManageQuickAssignmentsTestCase(QuickAssignTestCase):
    def detail(self, quick_assignment):
        return reverse(
            f"{QUICK_ASSIGNMENTS}-detail", kwargs={"pk": quick_assignment.pk}
        )

    def test_coaches_list_their_quick_assignments(self):
        quick_assignment = self.make_quick_assignment(exercise_ids=[EXERCISE_ID])
        self.client.post(
            join_url(quick_assignment.token), {"full_name": "Ada"}, format="json"
        )
        other_coach = self.user("other")
        self.facility.add_role(other_coach, role_kinds.COACH)
        self.sign_in(other_coach)
        self.create(web_page=WEB_PAGE)
        self.client.logout()
        self.sign_in(self.coach)

        response = self.client.get(reverse(f"{QUICK_ASSIGNMENTS}-list"))

        self.assertEqual(
            [
                (item["title"], item["token"], item["learner_count"], item["is_open"])
                for item in response.data
            ],
            [("Two-step equations", quick_assignment.token, 1, True)],
        )
        self.assertEqual(
            response.data[0]["link"],
            f"http://testserver/join/{quick_assignment.token}",
        )

    def test_the_link_opens_the_join_page(self):
        quick_assignment = self.make_quick_assignment(exercise_ids=[EXERCISE_ID])

        response = self.client.get(
            reverse(JOIN_LINK_URL_NAME, args=[quick_assignment.token])
        )

        self.assertRedirects(
            response,
            f"/en/quick_assign/#/{quick_assignment.token}",
            fetch_redirect_response=False,
        )

    def test_coaches_stop_new_people_joining(self):
        quick_assignment = self.make_quick_assignment(exercise_ids=[EXERCISE_ID])
        self.sign_in(self.coach)

        response = self.client.patch(
            self.detail(quick_assignment), {"is_open": False}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        quick_assignment.refresh_from_db()
        self.assertFalse(quick_assignment.is_open)

    def test_other_coaches_cannot_change_them(self):
        quick_assignment = self.make_quick_assignment(exercise_ids=[EXERCISE_ID])
        other_coach = self.user("other")
        self.facility.add_role(other_coach, role_kinds.COACH)
        self.sign_in(other_coach)

        response = self.client.patch(
            self.detail(quick_assignment), {"is_open": False}, format="json"
        )

        self.assertEqual(response.status_code, 404)


class JoinTestCase(QuickAssignTestCase):
    def setUp(self):
        super().setUp()
        self.quick_assignment = self.make_quick_assignment(exercise_ids=[EXERCISE_ID])
        self.url = link_url(self.quick_assignment.token)

    def join(self, **data):
        return self.client.post(
            join_url(self.quick_assignment.token), data, format="json"
        )

    def signed_in_user(self):
        return FacilityUser.objects.get(pk=self.client.session["_auth_user_id"])

    def expire_session(self):
        # As Kolibri does after a while, leaving the browser's other cookies
        del self.client.cookies[settings.SESSION_COOKIE_NAME]

    def test_shows_what_the_link_is_for(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "title": "Two-step equations",
                "coach_name": "Ana Rivera",
                "is_open": True,
                "learner": None,
                "is_coach": False,
            },
        )

    def test_people_join_by_giving_their_name(self):
        response = self.join(full_name="  Ada Lovelace ")

        self.assertEqual(response.status_code, 200, response.data)
        user = self.signed_in_user()
        self.assertEqual(user.full_name, "Ada Lovelace")
        self.assertEqual(user.facility, self.facility)
        self.assertTrue(user.username.startswith("Ada_Lovelace_"))
        self.assertTrue(self.quick_assignment.group.get_members().filter(pk=user.pk))
        lesson = self.quick_assignment.lesson
        self.assertTrue(lesson.collection.get_members().filter(pk=user.pk))
        self.assertEqual(
            response.data,
            {
                "classroom_id": lesson.collection_id,
                "lesson_id": lesson.id,
                "contentnode_id": EXERCISE_ID,
                "web_page_id": None,
            },
        )

    def test_people_who_joined_cannot_sign_in_with_a_password(self):
        self.join(full_name="Ada Lovelace")
        user = self.signed_in_user()
        self.client.logout()

        self.assertFalse(self.client.login(username=user.username, password=""))

    def test_their_browser_signs_them_back_in(self):
        self.join(full_name="Ada Lovelace")
        user = self.signed_in_user()
        self.expire_session()

        self.assertEqual(
            self.client.get(self.url).data["learner"],
            {"full_name": "Ada Lovelace", "is_signed_in": False},
        )
        response = self.join()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.signed_in_user(), user)

    def test_someone_else_on_the_same_browser_joins_as_themselves(self):
        self.join(full_name="Ada Lovelace")
        first = self.signed_in_user()

        self.join(full_name="Grace Hopper")

        second = self.signed_in_user()
        self.assertNotEqual(second, first)
        self.expire_session()
        self.assertEqual(
            self.client.get(self.url).data["learner"]["full_name"], "Grace Hopper"
        )

    def test_a_changed_browser_key_signs_nobody_in(self):
        self.join(full_name="Ada Lovelace")
        user_id, _, key = self.client.cookies[BROWSER_KEY_COOKIE].value.partition(".")
        self.expire_session()
        self.client.cookies[BROWSER_KEY_COOKIE] = f"{user_id}.{key[:-1]}x"

        self.assertIsNone(self.client.get(self.url).data["learner"])
        self.assertEqual(self.join().status_code, 400)

    def test_signed_in_learners_join_as_themselves(self):
        learner = self.user("grace", full_name="Grace Hopper")
        self.sign_in(learner)

        self.assertEqual(
            self.client.get(self.url).data["learner"],
            {"full_name": "Grace Hopper", "is_signed_in": True},
        )
        self.join()

        self.assertTrue(self.quick_assignment.group.get_members().filter(pk=learner.pk))
        self.assertNotIn(BROWSER_KEY_COOKIE, self.client.cookies)

    def test_the_coach_is_not_added_as_a_learner(self):
        self.sign_in(self.coach)

        self.assertTrue(self.client.get(self.url).data["is_coach"])
        self.assertEqual(self.join().status_code, 403)
        self.assertFalse(self.quick_assignment.group.get_members().exists())

    def test_closed_links_only_let_people_who_joined_back_in(self):
        self.join(full_name="Ada Lovelace")
        self.expire_session()
        QuickAssignment.objects.update(is_open=False)

        self.assertEqual(self.join().status_code, 200)
        self.client.logout()
        self.client.cookies.clear()
        self.assertEqual(self.join(full_name="Grace Hopper").status_code, 403)

    def test_needs_a_name(self):
        self.assertEqual(self.join(full_name="   ").status_code, 400)
        self.assertEqual(self.join().status_code, 400)

    def test_unknown_links_are_not_found(self):
        self.assertEqual(self.client.get(link_url("nothing-here")).status_code, 404)

    def test_answers_of_people_who_joined_count_in_the_lesson(self):
        self.join(full_name="Ada Lovelace")
        lesson = self.quick_assignment.lesson

        session = self.client.post(
            reverse("kolibri:core:trackprogress-list"),
            {
                "node_id": EXERCISE_ID,
                "content_id": EXERCISE_ID,
                "channel_id": CHANNEL_ID,
                "kind": content_kinds.EXERCISE,
                "lesson_id": lesson.id,
                "mastery_model": {"type": "m_of_n", "m": 3, "n": 3},
            },
            format="json",
        )
        self.assertEqual(session.status_code, 200, session.data)
        answer = self.client.put(
            reverse(
                "kolibri:core:trackprogress-detail",
                kwargs={"pk": session.data["session_id"]},
            ),
            {
                "interactions": [
                    {
                        "item": "question-1",
                        "correct": 1,
                        "time_spent": 5,
                        "answer": {"response": "4"},
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(answer.status_code, 200, answer.data)
        self.assertTrue(
            AttemptLog.objects.filter(user=self.signed_in_user(), correct=1).exists()
        )

    def test_web_page_assignments_open_the_web_page(self):
        quick_assignment = self.make_quick_assignment(web_page=WEB_PAGE)

        response = self.client.post(
            join_url(quick_assignment.token), {"full_name": "Ada"}, format="json"
        )

        web_page = LessonWebPage.objects.get(lesson=quick_assignment.lesson)
        self.assertEqual(response.data["web_page_id"], web_page.id)
        self.assertIsNone(response.data["contentnode_id"])
