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
from django.core.management.base import BaseCommand
from le_utils.constants import content_kinds

from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode

logger = logging.getLogger(__name__)

EXPORT_URL = "https://storage.googleapis.com/public-content-export-data/{language}-export-recent.tsv"

# The Kolibri language codes Khan Academy's export names differently
EXPORT_LANGUAGES = {
    "fuv": "fv",
    "pt-BR": "pt",
    "pt-PT": "pt-pt",
    "zh-CN": "zh-hans",
}

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


class Command(BaseCommand):
    help = (
        "Record the YouTube ids of the videos in Khan Academy channels, from Khan "
        "Academy's public content export, so they can play from YouTube. Run it "
        "again after updating a channel."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "channel_ids",
            nargs="*",
            help="The channels to look in. All channels when none are given.",
        )
        parser.add_argument(
            "--export",
            help="A downloaded export file to read, instead of downloading the "
            "export for each channel's language",
        )

    def handle(self, *args, **options):
        channels = ChannelMetadata.objects.all()
        if options["channel_ids"]:
            channels = channels.filter(id__in=options["channel_ids"])
        channels_by_language = defaultdict(list)
        for channel_id, language in channels.values_list("id", "root__lang_id"):
            channels_by_language[language].append(channel_id)

        for language, channel_ids in channels_by_language.items():
            videos = ContentNode.objects.filter(
                channel_id__in=channel_ids, kind=content_kinds.VIDEO
            )
            content_ids = set(videos.values_list("content_id", flat=True))
            if not content_ids:
                continue
            source = options["export"] or EXPORT_URL.format(
                language=EXPORT_LANGUAGES.get(language, language)
            )
            with open_export(source) as export:
                if export is None:
                    logger.info("Khan Academy has no export in %s", language)
                    continue
                youtube_ids = read_youtube_ids(export, content_ids)

            found = 0
            updated = []
            for video in videos.only("id", "content_id", "options"):
                youtube_id = youtube_ids.get(video.content_id)
                if not youtube_id:
                    continue
                found += 1
                video_options = video.options or {}
                if video_options.get("youtube_id") != youtube_id:
                    video.options = {**video_options, "youtube_id": youtube_id}
                    updated.append(video)
            ContentNode.objects.bulk_update(updated, ["options"], batch_size=500)
            logger.info(
                "Found YouTube ids for %d of the %d videos in %s, %d of them new",
                found,
                videos.count(),
                language,
                len(updated),
            )
