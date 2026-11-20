from unittest.mock import patch

from django.test import TestCase

from kolibri.core.content.utils.paths import zip_content_static_root
from kolibri.plugins.media_player.kolibri_plugin import MediaPlayerAsset
from kolibri.utils import conf


class YouTubePlaybackOptionTestCase(TestCase):
    def test_off_by_default(self):
        self.assertFalse(conf.OPTIONS["MediaPlayer"]["YOUTUBE_PLAYBACK"])
        self.assertEqual(MediaPlayerAsset().plugin_data, {})

    def test_gives_the_youtube_player_on_the_content_origin_when_on(self):
        with patch.dict(conf.OPTIONS["MediaPlayer"], {"YOUTUBE_PLAYBACK": True}):
            data = MediaPlayerAsset().plugin_data

        self.assertEqual(
            data["youtubePlayerUrl"], zip_content_static_root() + "youtube/player.html"
        )
