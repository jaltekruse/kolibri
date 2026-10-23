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
