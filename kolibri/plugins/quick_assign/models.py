import secrets

from django.db import models

from kolibri.core.auth.models import AdHocGroup
from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import FacilityUser
from kolibri.core.lessons.models import Lesson

# None of these are synced to other devices, so quick assignments only work on the
# device they were made on, like the lesson web pages they can include.


def new_link_token():
    return secrets.token_urlsafe(12)


class QuickAssignClassroom(models.Model):
    """
    The class a coach's quick assignments are in, made with their first one, so a
    coach can share an assignment before setting up any classes.
    """

    coach = models.OneToOneField(
        FacilityUser,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="quick_assign_classroom",
    )
    classroom = models.OneToOneField(
        Classroom, on_delete=models.CASCADE, related_name="+"
    )

    class Meta:
        db_table = "quick_assign_classroom"


class QuickAssignment(models.Model):
    """
    A lesson that anyone with its link can join by giving their name. The lesson is
    assigned to a group of the learners who joined through the link.
    """

    lesson = models.OneToOneField(
        Lesson,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="quick_assignment",
    )
    group = models.OneToOneField(AdHocGroup, on_delete=models.CASCADE, related_name="+")
    # The secret part of the link
    token = models.CharField(max_length=32, unique=True, default=new_link_token)
    # Whether people who have not joined yet can join through the link
    is_open = models.BooleanField(default=True)

    class Meta:
        db_table = "quick_assign_quickassignment"


class LinkLearner(models.Model):
    """
    A learner who joined through a quick assignment link by giving their name. They
    have no password, so their browser keeps a key that signs them back in.
    """

    user = models.OneToOneField(
        FacilityUser,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="link_learner",
    )
    # A hash of the key, so a copy of the database cannot sign anyone in
    key_hash = models.CharField(max_length=64)

    class Meta:
        db_table = "quick_assign_linklearner"
