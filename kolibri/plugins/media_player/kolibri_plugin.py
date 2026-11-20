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


def _options_with(field, key, value_start):
    # Options are stored as JSON text, written with or without spaces
    return Q(**{f"{field}__contains": f'"{key}": {value_start}'}) | Q(
        **{f"{field}__contains": f'"{key}":{value_start}'}
    )


@register_hook
class YouTubeVideosHook(content_hooks.StreamedContentHook):
    """
    With YOUTUBE_PLAYBACK on, a video with a YouTube id plays from YouTube, so its
    own files can be left out. Its thumbnail and subtitles are still wanted.
    """

    @property
    def enabled(self):
        return conf.OPTIONS["MediaPlayer"]["YOUTUBE_PLAYBACK"]

    def streamed_files(self):
        options = "contentnode__options"
        return (
            Q(contentnode__kind=content_kinds.VIDEO, supplementary=False)
            & _options_with(options, "youtube_id", '"')
            & ~_options_with(options, "youtube_id", '""')
        )


@register_hook
class KhanAcademyYouTubeIdsHook(content_hooks.ChannelImportHook):
    """
    Importing a Khan Academy channel, or a new version of one, replaces its
    videos' options, so their YouTube ids are looked up again.
    """

    def channel_imported(self, channel_id):
        # Plugins load before Django's apps, so models and tasks are imported here
        from kolibri.plugins.media_player.khan_academy import is_khan_academy_channel  # noqa: PLC0415
        from kolibri.plugins.media_player.tasks import add_khan_academy_youtube_ids  # noqa: PLC0415

        if conf.OPTIONS["MediaPlayer"]["YOUTUBE_PLAYBACK"] and is_khan_academy_channel(
            channel_id
        ):
            add_khan_academy_youtube_ids.enqueue(args=(channel_id,))
