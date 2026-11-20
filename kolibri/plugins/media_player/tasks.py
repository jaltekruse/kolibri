from kolibri.core.tasks.decorators import register_task
from kolibri.plugins.media_player.khan_academy import add_youtube_ids


@register_task
def add_khan_academy_youtube_ids(channel_id):
    """
    Record the YouTube ids of a Khan Academy channel's videos, from Khan Academy's
    export, which for English is about 320 MB.
    """
    add_youtube_ids([channel_id])
