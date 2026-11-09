import json
import uuid

from django.urls import reverse
from le_utils.constants import content_kinds
from rest_framework.status import HTTP_200_OK
from rest_framework.status import HTTP_201_CREATED
from rest_framework.status import HTTP_403_FORBIDDEN

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.test.helpers import DUMMY_PASSWORD
from kolibri.core.auth.test.helpers import KolibriAPITestCase as APITestCase
from kolibri.core.auth.test.helpers import provision_device
from kolibri.core.auth.test.test_api import FacilityFactory
from kolibri.core.auth.test.test_api import FacilityUserFactory
from kolibri.core.content.models import ContentNode
from kolibri.core.logger.models import ContentFeedbackLog
from kolibri.core.logger.models import ContentSummaryLog


class ContentFeedbackLogAPITestCase(APITestCase):
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
        cls.other_coach = FacilityUserFactory(facility=cls.facility)
        cls.other_classroom.add_coach(cls.other_coach)
        cls.content_id = uuid.uuid4().hex
        cls.url = reverse("kolibri:core:contentfeedbacklog-list")

    def login(self, user):
        self.client.login(
            username=user.username, password=DUMMY_PASSWORD, facility=self.facility
        )

    def give_feedback(self, learner, data):
        return self.client.post(
            self.url,
            {"user": learner.id, "content_id": self.content_id, "data": data},
            format="json",
        )

    def test_coach_gives_feedback(self):
        self.login(self.coach)
        response = self.give_feedback(self.learner, {"score": 3})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        feedback = ContentFeedbackLog.objects.get(
            user=self.learner, content_id=self.content_id
        )
        self.assertEqual(feedback.data, {"score": 3})

    def test_giving_feedback_again_updates_it(self):
        self.login(self.coach)
        self.give_feedback(self.learner, {"score": 3})
        response = self.give_feedback(self.learner, {"score": 5})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        feedback = ContentFeedbackLog.objects.get(
            user=self.learner, content_id=self.content_id
        )
        self.assertEqual(feedback.data, {"score": 5})
        self.assertEqual(
            ContentFeedbackLog.objects.filter(user=self.learner).count(), 1
        )

    def test_coach_of_another_class_cannot_give_feedback(self):
        self.login(self.other_coach)
        response = self.give_feedback(self.learner, {"score": 3})
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(ContentFeedbackLog.objects.exists())

    def test_learner_cannot_give_themselves_feedback(self):
        self.login(self.learner)
        response = self.give_feedback(self.learner, {"score": 5})
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(ContentFeedbackLog.objects.exists())

    def test_learner_reads_their_feedback(self):
        ContentFeedbackLog.objects.create(
            user=self.learner, content_id=self.content_id, data={"score": 3}
        )
        ContentFeedbackLog.objects.create(
            user=self.other_learner, content_id=self.content_id, data={"score": 1}
        )
        self.login(self.learner)
        response = self.client.get(self.url, {"content_id": self.content_id})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual([entry["data"] for entry in response.data], [{"score": 3}])

    def test_coach_lists_feedback_for_their_class(self):
        ContentFeedbackLog.objects.create(
            user=self.learner, content_id=self.content_id, data={"score": 3}
        )
        ContentFeedbackLog.objects.create(
            user=self.other_learner, content_id=self.content_id, data={"score": 1}
        )
        self.login(self.coach)
        response = self.client.get(
            self.url, {"content_id": self.content_id, "classroom": self.classroom.id}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual([entry["user"] for entry in response.data], [self.learner.id])


class FeedbackInProgressTrackingTestCase(APITestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        provision_device()
        cls.facility = FacilityFactory.create()
        cls.learner = FacilityUserFactory(facility=cls.facility)
        cls.node = ContentNode.objects.create(
            id=uuid.uuid4().hex,
            content_id=uuid.uuid4().hex,
            channel_id=uuid.uuid4().hex,
            kind=content_kinds.HTML5,
            title="Resource",
        )

    def setUp(self):
        self.client.login(
            username=self.learner.username,
            password=DUMMY_PASSWORD,
            facility=self.facility,
        )

    def start_session(self):
        return self.client.post(
            reverse("kolibri:core:trackprogress-list"),
            {
                "node_id": self.node.id,
                "content_id": self.node.content_id,
                "channel_id": self.node.channel_id,
                "kind": self.node.kind,
            },
            format="json",
        ).data

    def save_work(self, session_id, storage):
        return self.client.put(
            reverse("kolibri:core:trackprogress-detail", kwargs={"pk": session_id}),
            {"extra_fields": {"contentState": {"localStorage": storage}}},
            format="json",
        )

    def test_resource_gets_feedback_in_its_storage(self):
        session = self.start_session()
        self.save_work(session["session_id"], {"work": "1"})
        ContentFeedbackLog.objects.create(
            user=self.learner, content_id=self.node.content_id, data={"score": 3}
        )
        session = self.start_session()
        self.assertEqual(
            session["extra_fields"]["contentState"]["localStorage"],
            {"work": "1", "kolibri:feedback": json.dumps({"score": 3})},
        )

    def test_resource_storage_without_feedback(self):
        session = self.start_session()
        self.assertNotIn("contentState", session["extra_fields"])

    def test_feedback_not_saved_with_work(self):
        session = self.start_session()
        self.save_work(
            session["session_id"],
            {"work": "1", "kolibri:feedback": json.dumps({"score": 5})},
        )
        summarylog = ContentSummaryLog.objects.get(user=self.learner)
        self.assertEqual(
            summarylog.extra_fields["contentState"]["localStorage"], {"work": "1"}
        )
