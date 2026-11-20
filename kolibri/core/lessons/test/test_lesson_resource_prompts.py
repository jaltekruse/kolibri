import uuid

from django.urls import reverse

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.lessons.models import Lesson

DUMMY_PASSWORD = "password"


def _resource(**extra):
    return {
        "contentnode_id": uuid.uuid4().hex,
        "content_id": uuid.uuid4().hex,
        "channel_id": uuid.uuid4().hex,
        **extra,
    }


def _prompt(text="What is the main idea of section 2?"):
    return {"id": uuid.uuid4().hex, "text": text}


class LessonResourcePromptsTestCase(APITestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        provision_device()
        cls.facility = Facility.objects.create(name="MyFac")
        cls.admin = FacilityUser.objects.create(username="admin", facility=cls.facility)
        cls.admin.set_password(DUMMY_PASSWORD)
        cls.admin.save()
        cls.facility.add_admin(cls.admin)
        cls.classroom = Classroom.objects.create(name="Classroom", parent=cls.facility)

    def setUp(self):
        self.lesson = Lesson.objects.create(
            title="title",
            is_active=True,
            collection=self.classroom,
            created_by=self.admin,
        )
        self.client.login(username=self.admin.username, password=DUMMY_PASSWORD)

    def _patch_resources(self, resources):
        return self.client.patch(
            reverse("kolibri:core:lesson-detail", kwargs={"pk": self.lesson.id}),
            {"resources": resources},
            format="json",
        )

    def test_prompts_are_saved_on_resource(self):
        prompts = [_prompt("First question"), _prompt("Second question")]
        response = self._patch_resources([_resource(prompts=prompts)])
        self.assertEqual(response.status_code, 200)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.resources[0]["prompts"], prompts)

    def test_resource_without_prompts_has_no_prompts_key(self):
        response = self._patch_resources([_resource()])
        self.assertEqual(response.status_code, 200)
        self.lesson.refresh_from_db()
        self.assertNotIn("prompts", self.lesson.resources[0])

    def test_prompts_survive_resource_reorder(self):
        with_prompts = _resource(prompts=[_prompt()])
        without_prompts = _resource()
        self._patch_resources([with_prompts, without_prompts])
        response = self._patch_resources([without_prompts, with_prompts])
        self.assertEqual(response.status_code, 200)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.resources[1]["prompts"], with_prompts["prompts"])

    def test_duplicate_prompt_ids_rejected(self):
        prompt = _prompt()
        response = self._patch_resources([_resource(prompts=[prompt, prompt])])
        self.assertEqual(response.status_code, 400)

    def test_blank_prompt_text_rejected(self):
        response = self._patch_resources([_resource(prompts=[_prompt(text="")])])
        self.assertEqual(response.status_code, 400)

    def test_invalid_prompt_id_rejected(self):
        response = self._patch_resources(
            [_resource(prompts=[{"id": "not-a-uuid", "text": "Question"}])]
        )
        self.assertEqual(response.status_code, 400)
