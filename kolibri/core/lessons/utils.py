"""
Resources can ask, with the progress_per_lesson option, for learners' progress on them to be kept for each lesson they
are in, like a tool learners do a different assignment in for each lesson, rather than once for the resource. Their
progress is then kept under a content_id for the resource in the lesson, which is the content_id of the resource in
the lesson's resources.
"""

import uuid

from kolibri.core.content.models import ContentNode

# The ContentNode option a resource sets to have learners' progress on it kept for each lesson it is in
PROGRESS_PER_LESSON = "progress_per_lesson"

_LESSON_CONTENT_ID_NAMESPACE = uuid.UUID("1f3c0a8e-6b0f-4d5e-9a63-2a7a4e5b8c11")


def lesson_content_id(lesson_id, content_id):
    """The content_id learners' progress on a resource in a lesson is kept under, when it's kept for each lesson"""
    return uuid.uuid5(
        _LESSON_CONTENT_ID_NAMESPACE,
        f"{uuid.UUID(lesson_id).hex}:{uuid.UUID(content_id).hex}",
    ).hex


def progress_per_lesson(options):
    return bool((options or {}).get(PROGRESS_PER_LESSON))


def nodes_with_progress_per_lesson(node_ids):
    """{node id: content_id} for the resources among node_ids that keep progress for each lesson"""
    return {
        node_id: content_id
        for node_id, content_id, options in ContentNode.objects.filter_by_uuids(
            node_ids
        ).values_list("id", "content_id", "options")
        if progress_per_lesson(options)
    }
