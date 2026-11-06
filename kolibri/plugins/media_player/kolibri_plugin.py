from django.db.models import Q
from le_utils.constants import content_kinds
from le_utils.constants import format_presets

from kolibri.core.content import hooks as content_hooks
from kolibri.core.content.utils.paths import zip_content_static_root
from kolibri.core.utils.urls import join_url
from kolibri.plugins import KolibriPluginBase
from kolibri.plugins.hooks import register_hook
from kolibri.utils import conf

# In this plugin's static directory, which the content origin serves
YOUTUBE_PLAYER_PATH = "youtube/player.html"


class MediaPlayerPlugin(KolibriPluginBase):
    kolibri_options = "options"


@register_hook
class MediaPlayerAsset(content_hooks.ContentViewerHook):
    bundle_id = "main"
    presets = (
        format_presets.AUDIO,
        format_presets.VIDEO_HIGH_RES,
        format_presets.VIDEO_LOW_RES,
    )
    css_selectors = ("video", "audio")
    allow_object_tag = True  # Media player can handle object tags for audio/video
    # The YouTube player page, kept apart from Kolibri's origin
    sandbox_static = True

    @property
    def plugin_data(self):
        if not conf.OPTIONS["MediaPlayer"]["YOUTUBE_PLAYBACK"]:
            return {}
        return {
            "youtubePlayerUrl": join_url(zip_content_static_root(), YOUTUBE_PLAYER_PATH)
        }


def _options_with(key, value_start):
    # Options are stored as JSON text, written with or without spaces
    return Q(options__contains=f'"{key}": {value_start}') | Q(
        options__contains=f'"{key}":{value_start}'
    )


@register_hook
class YouTubeVideosHook(content_hooks.StreamedContentHook):
    """
    With YOUTUBE_PLAYBACK on, a video with a YouTube id plays from YouTube, so it
    needn't have its files on the device.
    """

    @property
    def enabled(self):
        return conf.OPTIONS["MediaPlayer"]["YOUTUBE_PLAYBACK"]

    def playable_without_files(self):
        return (
            Q(kind=content_kinds.VIDEO)
            & _options_with("youtube_id", '"')
            & ~_options_with("youtube_id", '""')
        )

    def files_to_stream(self):
        # A Khan Academy video's YouTube id is looked up after its channel is
        # imported, so any video's own files can be left out: its thumbnail and
        # subtitles are still wanted
        return Q(contentnode__kind=content_kinds.VIDEO, supplementary=False)


@register_hook
class KhanAcademyYouTubeIdsHook(content_hooks.ChannelImportHook):
    """
    Importing a Khan Academy channel, or a new version of one, replaces its
    videos' options, so their YouTube ids are looked up again.
    """

    def channel_imported(self, channel_id):
        # Plugins load before Django's apps, so models and tasks are imported here
        from kolibri.plugins.media_player.khan_academy import (  # noqa: PLC0415
            is_khan_academy_channel,
        )
        from kolibri.plugins.media_player.tasks import (  # noqa: PLC0415
            add_khan_academy_youtube_ids,
        )

        if conf.OPTIONS["MediaPlayer"]["YOUTUBE_PLAYBACK"] and is_khan_academy_channel(
            channel_id
        ):
            add_khan_academy_youtube_ids.enqueue(args=(channel_id,))
