import os
import tempfile
import uuid

from django.test import TestCase
from le_utils.constants import content_kinds
from le_utils.constants import format_presets

from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import File
from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.annotation import update_content_metadata
from kolibri.core.content.utils.channels import CHANNEL_UPDATE_STATS_CACHE_KEY
from kolibri.core.content.utils.content_types_tools import renderable_preset_bits
from kolibri.core.content.utils.import_export_content import get_import_export_data
from kolibri.core.content.utils.upgrade import get_import_data_for_update
from kolibri.core.utils.cache import process_cache
from kolibri.plugins.media_player.khan_academy import add_youtube_ids
from kolibri.utils.tests.helpers import override_option

from .test_add_khan_academy_youtube_ids import KhanAcademyChannelsMixin

YOUTUBE_ID = "5a6zpfl50go"


class YouTubeStreamingTestCase(KhanAcademyChannelsMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.youtube_playback(True)
        self.channel = self.create_channel("en")
        self.video = self.create_video(
            self.channel, YOUTUBE_ID, options={"youtube_id": YOUTUBE_ID}
        )
        self.mp4 = self.add_file(self.video, format_presets.VIDEO_HIGH_RES, "mp4")
        self.subtitles = self.add_file(
            self.video, format_presets.VIDEO_SUBTITLE, "vtt", supplementary=True
        )
        self.thumbnail = self.add_file(
            self.video,
            format_presets.VIDEO_THUMBNAIL,
            "png",
            supplementary=True,
            thumbnail=True,
        )

    def youtube_playback(self, on):
        option = override_option("MediaPlayer", "YOUTUBE_PLAYBACK", on)
        option.enable()
        self.addCleanup(option.disable)

    def add_file(self, node, preset, extension, supplementary=False, thumbnail=False):
        local_file = LocalFile.objects.create(
            id=uuid.uuid4().hex, extension=extension, available=False, file_size=10
        )
        File.objects.create(
            id=uuid.uuid4().hex,
            local_file=local_file,
            contentnode=node,
            preset=preset,
            supplementary=supplementary,
            thumbnail=thumbnail,
            # As a channel's import sets it, for its renderer
            included_presets=renderable_preset_bits.get(preset),
        )
        return local_file

    def import_video(self):
        update_content_metadata(
            self.channel.channel_id, node_ids=[self.video.id], admin_imported=True
        )

    def available(self, node):
        node.refresh_from_db()
        return node.available

    def test_an_imported_video_with_a_youtube_id_is_available_without_its_files(self):
        self.import_video()

        self.assertTrue(self.available(self.video))
        self.assertTrue(self.available(self.channel))

    def test_a_video_that_was_not_imported_is_not_available(self):
        update_content_metadata(self.channel.channel_id)

        self.assertFalse(self.available(self.video))

    def test_a_video_without_a_youtube_id_needs_its_files(self):
        self.video.options = {}
        self.video.save()

        self.import_video()

        self.assertFalse(self.available(self.video))

    def test_videos_need_their_files_without_youtube_playback(self):
        self.youtube_playback(False)

        self.import_video()

        self.assertFalse(self.available(self.video))

    def files_to_import(self, stream):
        _, files, _ = get_import_export_data(
            self.channel.channel_id,
            [self.channel.id],
            available=False,
            stream=stream,
        )
        return {f["id"] for f in files}

    def test_an_import_asked_to_stream_leaves_out_videos_own_files(self):
        exercise = ContentNode.objects.create(
            id=uuid.uuid4().hex,
            title="Practice",
            content_id=uuid.uuid4().hex,
            channel_id=self.channel.channel_id,
            parent=self.channel,
            kind=content_kinds.EXERCISE,
        )
        perseus = self.add_file(exercise, format_presets.EXERCISE, "perseus")

        self.assertEqual(
            self.files_to_import(stream=True),
            {self.subtitles.id, self.thumbnail.id, perseus.id},
        )
        self.assertIn(self.mp4.id, self.files_to_import(stream=False))

    def test_videos_that_get_a_youtube_id_after_their_import_become_available(self):
        self.video.options = {}
        self.video.save()
        self.import_video()
        self.assertFalse(self.available(self.video))
        # Elsewhere in the channel, with its file on the device, but not imported
        elsewhere = ContentNode.objects.create(
            id=uuid.uuid4().hex,
            title="Practice, elsewhere",
            content_id=uuid.uuid4().hex,
            channel_id=self.channel.channel_id,
            parent=self.channel,
            kind=content_kinds.EXERCISE,
        )
        exercise_file = self.add_file(elsewhere, format_presets.EXERCISE, "perseus")
        LocalFile.objects.filter(id=exercise_file.id).update(available=True)

        with tempfile.NamedTemporaryFile(
            "w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as export:
            export.write(f"kind\tid\tyoutube_id\nVideo\tx1\t{YOUTUBE_ID}\n")
        self.addCleanup(os.remove, export.name)
        add_youtube_ids([self.channel.channel_id], export=export.name)

        self.assertTrue(self.available(self.video))
        self.assertFalse(self.available(elsewhere))

    def test_a_channel_update_keeps_streaming_videos_that_stream(self):
        self.import_video()
        process_cache.set(
            CHANNEL_UPDATE_STATS_CACHE_KEY.format(self.channel.channel_id),
            {"updated_resource_ids": [self.video.id]},
        )
        self.addCleanup(
            process_cache.delete,
            CHANNEL_UPDATE_STATS_CACHE_KEY.format(self.channel.channel_id),
        )

        _, files, _ = get_import_data_for_update(self.channel.channel_id)

        self.assertEqual(
            {f["id"] for f in files}, {self.subtitles.id, self.thumbnail.id}
        )
