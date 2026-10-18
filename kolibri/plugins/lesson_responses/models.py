from uuid import uuid4

from django.core.validators import URLValidator
from django.db import models
from morango.models import UUIDField

from kolibri.core.fields import DateTimeTzField
from kolibri.core.lessons.models import Lesson
from kolibri.utils.time_utils import local_now

from .utils import expand_problem_numbers

# Learners' browsers open these addresses, so only allow web pages
validate_web_page_url = URLValidator(schemes=["http", "https"])


class LessonWebPage(models.Model):
    """
    A page on the public web that a lesson asks learners to work from, such as
    exercises on an open educational resource site. Learners see the page next to
    the Free Math editor, with a problem for each number the coach listed.

    Unlike the lesson, a web page is not synced to other devices, so it only appears
    on the device where it was added. It is deleted with its lesson.
    """

    id = UUIDField(primary_key=True, default=uuid4)
    lesson = models.ForeignKey(
        Lesson, related_name="web_pages", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=2000, validators=[validate_web_page_url])
    # What to do on the page, such as which problems to solve
    instructions = models.TextField(blank=True, default="")
    # The problems learners show their work on, as the coach wrote them,
    # such as "1-10, 21-35 by 3". See expand_problem_numbers.
    problem_numbers = models.CharField(max_length=500)
    date_created = DateTimeTzField(default=local_now, editable=False)

    class Meta:
        db_table = "lesson_responses_lessonwebpage"
        ordering = ("date_created",)

    @property
    def problems(self):
        return expand_problem_numbers(self.problem_numbers)
