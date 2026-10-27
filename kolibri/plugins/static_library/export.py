"""
Writes the library as files a static web host can serve. Each file goes where its
URL on this Kolibri points, under the output folder, so serve that folder as the
site's root and open the page at URL_PATH_PREFIX:

    <URL_PATH_PREFIX>index.html       the page, the static_library app
    <URL_PATH_PREFIX>static/          Kolibri's static files
    <URL_PATH_PREFIX>content/storage/ the channels' content files
    <ZIP_CONTENT_URL_PATH_PREFIX>content/zipcontent/ and content/static/
                                      archives unzipped, and the sandbox for them
    <URL_PATH_PREFIX>library/         what the page answers API requests from:
        channels.json                 channel/?available=true
        nodes/<id>.json               contentnode/<id>/
        children/<id>.json            a topic's children, serialized as by contentnode/
        index/<channel id>.json       the fields of each node that requests filter on
        library.json                  the channels' roots, their nodes' labels and
                                      what else answers requests without an index
        channel-thumbnails/           the channels' thumbnails

Only content API requests have answers here: the page is for guests, as in Learn.
"""

import json
import logging
import mimetypes
import os
import shutil
from base64 import urlsafe_b64decode
from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpRequest
from django.template.loader import render_to_string
from rest_framework.request import Request
from rest_framework.utils.encoders import JSONEncoder

from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.cache import get_course_ids
from kolibri.core.content.utils.paths import get_content_file_name
from kolibri.core.content.utils.paths import get_content_storage_file_path
from kolibri.core.content.utils.paths import get_content_url
from kolibri.core.content.utils.paths import get_local_content_storage_file_url
from kolibri.core.content.utils.paths import zip_content_path_prefix
from kolibri.core.content.utils.search import get_available_metadata_labels
from kolibri.core.content.utils.static_content import archive_files
from kolibri.core.content.utils.static_content import export_sandbox_static
from kolibri.core.content.utils.static_content import export_zip_content
from kolibri.core.content.utils.stopwords import stopwords_set
from kolibri.core.content.viewsets.channel_metadata import ChannelMetadataViewSet
from kolibri.core.content.viewsets.contentnode.base import ContentNodeViewset
from kolibri.core.content.viewsets.contentnode.filters import OptionalPagination
from kolibri.utils import translation

from .paths import library_data_url
from .paths import library_page_url

logger = logging.getLogger(__name__)

# Nodes serialized per query
BATCH_SIZE = 500

# The fields of each node in a channel's index, for filtering and searching
INDEX_FIELDS = (
    "id",
    "parent",
    "content_id",
    "tree_id",
    "lft",
    "rght",
    "kind",
    "title",
    "description",
    "coach_content",
    "modality",
    "lang_id",
    "in_course",
    "accessibility_labels",
    "categories",
    "grade_levels",
    "learner_needs",
    "learning_activities",
    "resource_types",
)

# How many of the library's first nodes library.json lists, to answer a request
# for a page of the whole library without loading every channel's index
FIRST_NODES = 25


def _path_for_url(output, url):
    return os.path.join(output, *url.lstrip("/").split("/"))


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        # As Kolibri's API renders it
        json.dump(data, f, cls=JSONEncoder, ensure_ascii=False, separators=(",", ":"))


def _link_or_copy(source, target):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.lexists(target):
        os.remove(target)
    try:
        os.link(source, target)
    except OSError:
        # Another filesystem
        shutil.copyfile(source, target)


def _write_channel_thumbnail(data_dir, channel):
    # As ChannelThumbnailView decodes it
    header, encoded = channel.thumbnail.split(",", 1)
    mimetype = header.split(":")[1].split(";")[0]
    filename = f"{channel.id}{mimetypes.guess_extension(mimetype) or ''}"
    path = os.path.join(data_dir, "channel-thumbnails", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(urlsafe_b64decode(encoded))
    return f"{library_data_url()}channel-thumbnails/{filename}"


def _export_channels(data_dir, channels):
    request = HttpRequest()
    request.method = "GET"
    serialized = ChannelMetadataViewSet().serialize_list(
        Request(request), {"available": "true"}
    )
    channel_ids = {channel.id for channel in channels}
    serialized = [channel for channel in serialized if channel["id"] in channel_ids]
    for item in serialized:
        if item["thumbnail"]:
            # A static host has no view to decode it
            item["thumbnail"] = _write_channel_thumbnail(
                data_dir, channels.get(id=item["id"])
            )
    _write_json(os.path.join(data_dir, "channels.json"), serialized)


def _serialized_nodes(channel_id):
    """Each available node of the channel, as contentnode/<id>/ returns it, in lft order."""
    viewset = ContentNodeViewset()
    ids = list(
        ContentNode.objects.filter(channel_id=channel_id, available=True)
        .order_by("lft")
        .values_list("id", flat=True)
    )
    for start in range(0, len(ids), BATCH_SIZE):
        yield from viewset.serialize(
            ContentNode.objects.filter(id__in=ids[start : start + BATCH_SIZE]).order_by(
                "lft"
            )
        )


def _index_row(node, course_ids):
    fields = {
        **node,
        "lang_id": node["lang"]["id"] if node["lang"] else None,
        "in_course": any(
            ancestor["id"] in course_ids for ancestor in node["ancestors"]
        ),
    }
    return [fields[field] for field in INDEX_FIELDS]


def _export_channel_nodes(data_dir, channel_id, course_ids):
    children = defaultdict(list)
    index = []
    for node in _serialized_nodes(channel_id):
        _write_json(os.path.join(data_dir, "nodes", f"{node['id']}.json"), node)
        if node["parent"]:
            children[node["parent"]].append(node)
        index.append(_index_row(node, course_ids))
    for parent, nodes in children.items():
        _write_json(os.path.join(data_dir, "children", f"{parent}.json"), nodes)
    _write_json(
        os.path.join(data_dir, "index", f"{channel_id}.json"),
        {"fields": INDEX_FIELDS, "rows": index},
    )


def _export_library_summary(data_dir, channels):
    nodes = ContentNode.objects.filter(
        channel_id__in=[channel.id for channel in channels], available=True
    )
    _write_json(
        os.path.join(data_dir, "library.json"),
        {
            "channels": [
                {
                    "id": channel.id,
                    "root": channel.root_id,
                    "tree_id": channel.root.tree_id,
                }
                for channel in channels
            ],
            "count": nodes.count(),
            "first_nodes": list(
                nodes.order_by(*OptionalPagination.ordering).values_list(
                    "id", flat=True
                )[:FIRST_NODES]
            ),
            "labels": get_available_metadata_labels(nodes),
            "course_ids": list(get_course_ids()),
            "stopwords": sorted(stopwords_set),
        },
    )


def export_library_data(output, channels):
    """Writes the JSON the page answers its API requests from."""
    data_dir = _path_for_url(output, library_data_url())
    course_ids = set(get_course_ids())
    _export_channels(data_dir, channels)
    for channel in channels:
        _export_channel_nodes(data_dir, channel.id, course_ids)
    _export_library_summary(data_dir, channels)


def export_content(output, channels):
    """Writes the channels' content files, and their archives unzipped."""
    channel_ids = [channel.id for channel in channels]
    local_files = LocalFile.objects.filter(
        available=True,
        files__contentnode__channel_id__in=channel_ids,
        files__contentnode__available=True,
    ).distinct()
    for local_file in local_files:
        target = _path_for_url(output, get_local_content_storage_file_url(local_file))
        source = get_content_storage_file_path(get_content_file_name(local_file))
        # Content files are named by checksum, so one already there is the same
        if os.path.exists(target):
            continue
        if not os.path.exists(source):
            # Kolibri can't serve it either
            logger.warning("Skipping %s, which is missing", source)
            continue
        _link_or_copy(source, target)
    zip_content_root = _path_for_url(output, get_content_url(zip_content_path_prefix()))
    export_sandbox_static(zip_content_root)
    for channel_id in channel_ids:
        export_zip_content(archive_files(channel_id), zip_content_root)


def export_static_files(output):
    """Writes Kolibri's static files, as collectstatic would."""
    root = _path_for_url(output, settings.STATIC_URL)
    ignore_patterns = apps.get_app_config("staticfiles").ignore_patterns
    written = set()
    for finder in finders.get_finders():
        for path, storage in finder.list(ignore_patterns):
            # The first one found is the one served
            if path not in written:
                written.add(path)
                _link_or_copy(storage.path(path), os.path.join(root, path))


def export_page(output):
    # Learn's pages, which this page reuses, are only translated in Learn's bundle
    with translation.override("en"):
        html = render_to_string("static_library/index.html")
    path = os.path.join(_path_for_url(output, library_page_url()), "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def available_channels(channel_ids=None):
    channels = ChannelMetadata.objects.filter(root__available=True).select_related(
        "root"
    )
    if channel_ids:
        channels = channels.filter(id__in=channel_ids)
    return channels


def export_library(output, channel_ids=None):
    channels = available_channels(channel_ids)
    export_library_data(output, channels)
    export_content(output, channels)
    export_static_files(output)
    export_page(output)
