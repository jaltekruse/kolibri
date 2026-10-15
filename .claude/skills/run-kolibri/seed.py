"""
Seed a provisioned dev Kolibri with something to click through, without Studio:

- class "Biology 101" in the device's facility
- coach "coach" (password "coach"), learners "ada" and "grace" (password "password")
- a local channel "Riverside Science Readings" holding a one-page PDF
- lesson "Photosynthesis" assigning that PDF to the class

Run inside Kolibri's Django shell (see SKILL.md). Safe to re-run: if the class
already exists it only prints the ids. Prints one JSON line with the ids.
"""

import hashlib
import json
import os
import sys
import uuid

from le_utils.constants import content_kinds
from le_utils.constants import format_presets
from le_utils.constants.labels import learning_activities

from kolibri.core.auth.models import Classroom
from kolibri.core.auth.models import Facility
from kolibri.core.auth.models import FacilityUser
from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import File
from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.annotation import set_channel_ancestors
from kolibri.core.content.utils.annotation import set_channel_metadata_fields
from kolibri.core.content.utils.annotation import set_content_visibility
from kolibri.core.content.utils.paths import get_content_storage_file_path
from kolibri.core.lessons.models import Lesson
from kolibri.core.lessons.models import LessonAssignment

CLASS_NAME = "Biology 101"
LESSON_TITLE = "Photosynthesis"


def make_pdf(lines):
    """A minimal valid one-page PDF showing the given lines of text."""
    text = " ".join(f"({line}) Tj T*" for line in lines)
    stream = f"BT /F1 14 Tf 72 720 Td 22 TL {text} ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()
    return out


def hexid():
    return uuid.uuid4().hex


def seed_channel():
    channel_id = hexid()
    root = ContentNode.objects.create(
        id=hexid(),
        content_id=hexid(),
        channel_id=channel_id,
        title="Riverside Science Readings",
        kind=content_kinds.TOPIC,
        available=True,
    )
    pdf_bytes = make_pdf(
        [
            "Photosynthesis: How Plants Make Food",
            "",
            "Plants capture light energy with a green pigment called chlorophyll.",
            "They combine carbon dioxide from the air with water from the soil",
            "to make glucose, a sugar, and release oxygen.",
            "",
            "Questions:",
            "1. What pigment captures light energy?",
            "2. Name the two inputs plants use to make glucose.",
            "3. Why is photosynthesis important for animals?",
        ]
    )
    checksum = hashlib.md5(pdf_bytes).hexdigest()
    path = get_content_storage_file_path(f"{checksum}.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    reading = ContentNode.objects.create(
        id=hexid(),
        content_id=hexid(),
        channel_id=channel_id,
        parent=root,
        title="Photosynthesis reading",
        description="A one-page reading about how plants make food.",
        kind=content_kinds.DOCUMENT,
        learning_activities=learning_activities.READ,
        license_name="CC BY",
        available=True,
    )
    LocalFile.objects.get_or_create(
        id=checksum,
        defaults={"extension": "pdf", "file_size": len(pdf_bytes), "available": True},
    )
    File.objects.create(
        id=hexid(),
        contentnode=reading,
        local_file_id=checksum,
        preset=format_presets.DOCUMENT,
        supplementary=False,
        thumbnail=False,
    )
    ChannelMetadata.objects.create(
        id=channel_id,
        name="Riverside Science Readings",
        description="Local test channel",
        root=root,
        version=1,
        min_schema_version="1",
        public=False,
    )
    set_content_visibility(channel_id, [checksum], admin_imported=True)
    set_channel_ancestors(channel_id)
    set_channel_metadata_fields(channel_id)
    return reading


def make_user(facility, username, password, full_name):
    user = FacilityUser.objects.create(
        username=username, full_name=full_name, facility=facility
    )
    user.set_password(password)
    user.save()
    return user


def seed():
    facility = Facility.get_default_facility()
    classroom = Classroom.objects.filter(name=CLASS_NAME, parent=facility).first()
    if classroom is None:
        reading = seed_channel()
        classroom = Classroom.objects.create(name=CLASS_NAME, parent=facility)
        coach = make_user(facility, "coach", "coach", "Coach Carter")
        facility.add_coach(coach)
        classroom.add_coach(coach)
        for username, name in (("ada", "Ada Lovelace"), ("grace", "Grace Hopper")):
            classroom.add_member(make_user(facility, username, "password", name))
        lesson = Lesson.objects.create(
            title=LESSON_TITLE,
            description="Read about photosynthesis and answer the questions.",
            collection=classroom,
            created_by=coach,
            is_active=True,
            resources=[
                {
                    "contentnode_id": reading.id,
                    "content_id": reading.content_id,
                    "channel_id": reading.channel_id,
                }
            ],
        )
        LessonAssignment.objects.create(
            lesson=lesson, collection=classroom, assigned_by=coach
        )
    lesson = Lesson.objects.get(title=LESSON_TITLE, collection=classroom)
    resource = lesson.resources[0]
    ids = {
        "class_id": classroom.id,
        "lesson_id": lesson.id,
        "contentnode_id": resource["contentnode_id"],
        "content_id": resource["content_id"],
    }
    sys.stdout.write(json.dumps(ids) + "\n")


seed()
