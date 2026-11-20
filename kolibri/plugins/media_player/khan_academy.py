"""
Khan Academy's videos are also on YouTube. Its chef sets each video's source_id
to the YouTube id of the English video, and a content_id is derived from the
source_id, so Khan Academy's public content export, which lists every video's
YouTube id, says which YouTube video each of its channels' videos is. Studio does
not publish source ids, so this matches them, and records the YouTube id in the
video's options, where the media player looks for it.
"""

import csv
import logging
import uuid
from collections import defaultdict
from contextlib import contextmanager
from io import TextIOWrapper

import requests
from le_utils.constants import content_kinds

from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.content.utils.annotation import set_streamed_content_availability

logger = logging.getLogger(__name__)

EXPORT_URL = "https://storage.googleapis.com/public-content-export-data/{language}-export-recent.tsv"

# The Kolibri language codes Khan Academy's export names differently
EXPORT_LANGUAGES = {
    "fuv": "fv",
    "pt-BR": "pt",
    "pt-PT": "pt-pt",
    "zh-CN": "zh-hans",
}

# The copyright holder of Khan Academy's videos
KHAN_ACADEMY = "Khan Academy"

# Ricecooker derives a content_id from the channel's source domain and the source_id
KHAN_ACADEMY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "khanacademy.org")

# Some of the export's fields, such as the ids of a course's children, are long
MAX_FIELD_SIZE = 2**31 - 1


@contextmanager
def open_export(source):
    if not source.startswith(("http://", "https://")):
        with open(source, encoding="utf-8", newline="") as export:
            yield export
        return
    with requests.get(source, stream=True, timeout=60) as response:
        if response.status_code == requests.codes.not_found:
            yield None
            return
        response.raise_for_status()
        response.raw.decode_content = True
        # urllib3 closes the response once the body is read, before the text
        # wrapper has read to its end, unless told not to
        response.raw.auto_close = False
        yield TextIOWrapper(response.raw, encoding="utf-8", newline="")


def read_youtube_ids(export, content_ids):
    """
    The YouTube id of each video in the export with one of these content_ids.
    """
    csv.field_size_limit(MAX_FIELD_SIZE)
    youtube_ids = {}
    for row in csv.DictReader(export, delimiter="\t"):
        if row["kind"] != "Video" or not row["youtube_id"]:
            continue
        content_id = uuid.uuid5(KHAN_ACADEMY_NAMESPACE, row["youtube_id"]).hex
        if content_id in content_ids:
            # A dubbed video is a different YouTube video from the English one
            youtube_ids[content_id] = (
                row.get("translated_youtube_id") or row["youtube_id"]
            )
    return youtube_ids


def is_khan_academy_channel(channel_id):
    """
    Whether a channel has Khan Academy's videos, which it holds the copyright of.
    """
    return ContentNode.objects.filter(
        channel_id=channel_id,
        kind=content_kinds.VIDEO,
        license_owner=KHAN_ACADEMY,
    ).exists()


def _record_youtube_ids(videos, youtube_ids):
    """
    Records each video's YouTube id, by content_id, in its options. Returns how many
    videos have one, and the videos whose id is new.
    """
    found = 0
    updated = []
    for video in videos.only("id", "channel_id", "content_id", "options"):
        youtube_id = youtube_ids.get(video.content_id)
        if not youtube_id:
            continue
        found += 1
        video_options = video.options or {}
        if video_options.get("youtube_id") != youtube_id:
            video.options = {**video_options, "youtube_id": youtube_id}
            updated.append(video)
    ContentNode.objects.bulk_update(updated, ["options"], batch_size=500)
    return found, updated


def add_youtube_ids(channel_ids=None, export=None):
    """
    Record the YouTube ids of the videos in these channels, or in all channels,
    from Khan Academy's export in each channel's language, or from this export file.
    """
    channels = ChannelMetadata.objects.all()
    if channel_ids:
        channels = channels.filter(id__in=channel_ids)
    channels_by_language = defaultdict(list)
    for channel_id, language in channels.values_list("id", "root__lang_id"):
        channels_by_language[language].append(channel_id)

    for language, language_channel_ids in channels_by_language.items():
        videos = ContentNode.objects.filter(
            channel_id__in=language_channel_ids, kind=content_kinds.VIDEO
        )
        content_ids = set(videos.values_list("content_id", flat=True))
        if not content_ids:
            continue
        source = export or EXPORT_URL.format(
            language=EXPORT_LANGUAGES.get(language, language)
        )
        with open_export(source) as rows:
            if rows is None:
                logger.info("Khan Academy has no export in %s", language)
                continue
            youtube_ids = read_youtube_ids(rows, content_ids)

        found, updated = _record_youtube_ids(videos, youtube_ids)
        # Imported videos that play from YouTube without their files are now
        # available
        for channel_id in {video.channel_id for video in updated}:
            set_streamed_content_availability(channel_id)
        logger.info(
            "Found YouTube ids for %d of the %d videos in %s, %d of them new",
            found,
            videos.count(),
            language,
            len(updated),
        )
