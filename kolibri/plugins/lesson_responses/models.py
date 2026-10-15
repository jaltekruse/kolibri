from django.db import models
from morango.models import UUIDField

from kolibri.core.auth.constants import role_kinds
from kolibri.core.auth.models import AbstractFacilityDataModel
from kolibri.core.auth.models import FacilityUser
from kolibri.core.auth.permissions.base import RoleBasedPermissions
from kolibri.core.auth.permissions.general import IsOwn
from kolibri.core.fields import DateTimeTzField
from kolibri.core.fields import JSONField
from kolibri.utils.time_utils import local_now


class LessonResponseFeedback(AbstractFacilityDataModel):
    """
    A coach's feedback on one learner's answers to the prompts on a lesson resource.
    It is synced only to that learner, so learner-only devices never hold
    other learners' feedback.
    """

    morango_model_name = "lessonresponsefeedback"

    permissions = IsOwn(read_only=True) | RoleBasedPermissions(
        target_field="user",
        can_be_created_by=(role_kinds.ADMIN, role_kinds.COACH),
        can_be_read_by=(role_kinds.ADMIN, role_kinds.COACH),
        can_be_updated_by=(role_kinds.ADMIN, role_kinds.COACH),
        can_be_deleted_by=(role_kinds.ADMIN, role_kinds.COACH),
        collection_field="user__memberships__collection_id",
    )

    # The learner the feedback is for
    user = models.ForeignKey(
        FacilityUser, related_name="lesson_response_feedback", on_delete=models.CASCADE
    )
    # Not foreign keys: learner-only devices hold lessons as serialized copies,
    # and content may not be imported on every device.
    lesson_id = UUIDField()
    contentnode_id = UUIDField()
    # Feedback on the learner's answers as a whole
    comment = models.TextField(blank=True)
    # Feedback on individual answers, keyed by prompt id
    prompt_comments = JSONField(default=dict, blank=True)
    date_modified = DateTimeTzField(default=local_now)

    class Meta:
        # Plugins are installed with their module path as the app label,
        # which would otherwise put dots in the table name.
        db_table = "lesson_responses_lessonresponsefeedback"

    def infer_dataset(self, *args, **kwargs):
        return self.cached_related_dataset_lookup("user")

    def calculate_source_id(self):
        # One feedback record per learner per lesson resource, even when
        # written on different devices.
        return f"{self.user_id}:{self.lesson_id}:{self.contentnode_id}"

    def calculate_partition(self):
        return f"{self.dataset_id}:user-ro:{self.user_id}"
