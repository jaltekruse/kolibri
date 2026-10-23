import io
import os
import tempfile
import uuid
from unittest.mock import MagicMock
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from le_utils.constants import content_kinds

from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import Language

KHAN_ACADEMY = uuid.uuid5(uuid.NAMESPACE_DNS, "khanacademy.org")

EN_EXPORT = (
    "kind\tid\tyoutube_id\n"
    "Video\tx1\t5a6zpfl50go\n"
    "Video\tx2\tnot_in_kolibri\n"
    "Course\tx3\t\n"
)

ES_EXPORT = (
    "kind\tid\tyoutube_id\ttranslated_youtube_id\n"
    "Video\tx1\t5a6zpfl50go\tdubbedEs123\n"
    "Video\tx4\tsubbedOnly1\t\n"
)


def khan_academy_content_id(youtube_id):
    return uuid.uuid5(KHAN_ACADEMY, youtube_id).hex


def fake_download(text, status_code=200):
    response = MagicMock(status_code=status_code)
    response.raw = io.BytesIO(text.encode("utf-8"))
    response.__enter__.return_value = response
    return response


class AddKhanAcademyYouTubeIdsTestCase(TestCase):
    def setUp(self):
        Language.objects.create(id="en", lang_code="en")
        Language.objects.create(id="es", lang_code="es")
        Language.objects.create(id="pt-BR", lang_code="pt", lang_subcode="BR")

    def create_channel(self, language):
        channel_id = uuid.uuid4().hex
        root = ContentNode.objects.create(
            id=uuid.uuid4().hex,
            title="Khan Academy",
            content_id=uuid.uuid4().hex,
            channel_id=channel_id,
            kind=content_kinds.TOPIC,
            lang_id=language,
        )
        ChannelMetadata.objects.create(id=channel_id, name="Khan Academy", root=root)
        return root

    def create_video(self, channel, youtube_id, options=None):
        return ContentNode.objects.create(
            id=uuid.uuid4().hex,
            title=youtube_id,
            content_id=khan_academy_content_id(youtube_id),
            channel_id=channel.channel_id,
            parent=channel,
            kind=content_kinds.VIDEO,
            options=options or {},
        )

    def run_with_export(self, text, *channel_ids):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as export:
            export.write(text)
        self.addCleanup(os.remove, export.name)
        call_command("add_khan_academy_youtube_ids", *channel_ids, export=export.name)

    def youtube_id(self, node):
        node.refresh_from_db()
        return node.options.get("youtube_id")

    def test_records_the_youtube_id_of_each_video_in_the_export(self):
        channel = self.create_channel("en")
        video = self.create_video(channel, "5a6zpfl50go")
        other = ContentNode.objects.create(
            id=uuid.uuid4().hex,
            title="Not from Khan Academy",
            content_id=uuid.uuid4().hex,
            channel_id=channel.channel_id,
            parent=channel,
            kind=content_kinds.VIDEO,
        )

        self.run_with_export(EN_EXPORT)

        self.assertEqual(self.youtube_id(video), "5a6zpfl50go")
        self.assertIsNone(self.youtube_id(other))

    def test_keeps_the_other_options(self):
        channel = self.create_channel("en")
        criteria = {"model": "time", "threshold": 120}
        video = self.create_video(
            channel, "5a6zpfl50go", options={"completion_criteria": criteria}
        )

        self.run_with_export(EN_EXPORT)

        video.refresh_from_db()
        self.assertEqual(
            video.options,
            {"completion_criteria": criteria, "youtube_id": "5a6zpfl50go"},
        )

    def test_a_dubbed_video_plays_the_dubbed_youtube_video(self):
        channel = self.create_channel("es")
        dubbed = self.create_video(channel, "5a6zpfl50go")
        subbed = self.create_video(channel, "subbedOnly1")

        self.run_with_export(ES_EXPORT)

        self.assertEqual(self.youtube_id(dubbed), "dubbedEs123")
        self.assertEqual(self.youtube_id(subbed), "subbedOnly1")

    def test_only_looks_in_the_channels_given(self):
        chosen = self.create_video(self.create_channel("en"), "5a6zpfl50go")
        other_channel = self.create_channel("en")
        not_chosen = self.create_video(other_channel, "5a6zpfl50go")

        self.run_with_export(EN_EXPORT, chosen.channel_id)

        self.assertEqual(self.youtube_id(chosen), "5a6zpfl50go")
        self.assertIsNone(self.youtube_id(not_chosen))

    @patch(
        "kolibri.plugins.media_player.management.commands.add_khan_academy_youtube_ids.requests.get"
    )
    def test_downloads_the_export_in_each_channels_language(self, get):
        english = self.create_video(self.create_channel("en"), "5a6zpfl50go")
        portuguese = self.create_video(self.create_channel("pt-BR"), "5a6zpfl50go")
        exports = {
            "https://storage.googleapis.com/public-content-export-data/en-export-recent.tsv": EN_EXPORT,
            "https://storage.googleapis.com/public-content-export-data/pt-export-recent.tsv": ES_EXPORT.replace(
                "dubbedEs123", "dubbedPt123"
            ),
        }
        get.side_effect = lambda url, **kwargs: fake_download(exports[url])

        call_command("add_khan_academy_youtube_ids")

        self.assertEqual(self.youtube_id(english), "5a6zpfl50go")
        self.assertEqual(self.youtube_id(portuguese), "dubbedPt123")

    @patch(
        "kolibri.plugins.media_player.management.commands.add_khan_academy_youtube_ids.requests.get"
    )
    def test_skips_a_language_khan_academy_has_no_export_in(self, get):
        get.return_value = fake_download("Not found", status_code=404)
        video = self.create_video(self.create_channel("es"), "5a6zpfl50go")

        call_command("add_khan_academy_youtube_ids")

        self.assertIsNone(self.youtube_id(video))
