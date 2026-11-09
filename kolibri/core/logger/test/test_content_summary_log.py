import uuid

from django.urls import reverse
from django.utils import timezone
from le_utils.constants import content_kinds
from rest_framework.status import HTTP_200_OK
from rest_framework.status import HTTP_412_PRECONDITION_FAILED

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.test.helpers import DUMMY_PASSWORD
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.auth.test.test_api import FacilityFactory
from kolibri.core.auth.test.test_api import FacilityUserFactory
from kolibri.core.logger.models import ContentSummaryLog


class ContentSummaryLogAPITestCase(APITestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        provision_device()
        cls.facility = FacilityFactory.create()
        cls.classroom = Classroom.objects.create(name="Class", parent=cls.facility)
        cls.other_classroom = Classroom.objects.create(
            name="Other class", parent=cls.facility
        )
        cls.learner = FacilityUserFactory(facility=cls.facility)
        cls.classroom.add_member(cls.learner)
        cls.other_learner = FacilityUserFactory(facility=cls.facility)
        cls.other_classroom.add_member(cls.other_learner)
        cls.coach = FacilityUserFactory(facility=cls.facility)
        cls.classroom.add_coach(cls.coach)
        cls.content_id = uuid.uuid4().hex
        for learner, work in ((cls.learner, "1"), (cls.other_learner, "2")):
            ContentSummaryLog.objects.create(
                user=learner,
                content_id=cls.content_id,
                start_timestamp=timezone.now(),
                kind=content_kinds.HTML5,
                extra_fields={"contentState": {"localStorage": {"work": work}}},
            )
        cls.url = reverse("kolibri:core:contentsummarylog-list")

    def login(self, user):
        self.client.login(
            username=user.username, password=DUMMY_PASSWORD, facility=self.facility
        )

    def test_coach_reads_work_of_learners_in_their_class(self):
        self.login(self.coach)
        response = self.client.get(
            self.url, {"content_id": self.content_id, "classroom": self.classroom.id}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            [(entry["user"], entry["extra_fields"]) for entry in response.data],
            [
                (
                    self.learner.id,
                    {"contentState": {"localStorage": {"work": "1"}}},
                )
            ],
        )

    def test_coach_cannot_read_work_of_learners_in_other_classes(self):
        self.login(self.coach)
        response = self.client.get(self.url, {"content_id": self.content_id})
        self.assertEqual([entry["user"] for entry in response.data], [self.learner.id])

    def test_learner_reads_only_their_work(self):
        self.login(self.learner)
        response = self.client.get(self.url, {"content_id": self.content_id})
        self.assertEqual([entry["user"] for entry in response.data], [self.learner.id])

    def test_content_id_required(self):
        self.login(self.coach)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTP_412_PRECONDITION_FAILED)
