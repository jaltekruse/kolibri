import json
import os
import shutil
import tempfile
import zipfile
from base64 import urlsafe_b64decode
from io import StringIO
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import File
from kolibri.core.content.models import LocalFile
from kolibri.core.webpack.hooks import WebpackBundleHook
from kolibri.plugins.static_library.export import available_channels
from kolibri.plugins.static_library.export import export_content
from kolibri.plugins.static_library.export import export_library_data
from kolibri.plugins.static_library.export import export_page
from kolibri.plugins.static_library.export import export_static_files
from kolibri.plugins.static_library.export import INDEX_FIELDS
from kolibri.utils.tests.helpers import override_option

CHANNEL_ID = "6199dde695db4ee4ab392222d5af1e5c"
THUMBNAIL = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABjElEQVR42mNk"
)


def built_bundle(hook):
    # The frontend isn't built for these tests, so each bundle is one made-up file
    return [{"name": f"{hook.unique_id}.js", "url": f"/static/{hook.unique_id}.js"}]


class StaticLibraryTestCase(APITestCase):
    fixtures = ["content_test.json"]  # noqa: RUF012

    @classmethod
    def setUpTestData(cls):
        ChannelMetadata.objects.filter(id=CHANNEL_ID).update(thumbnail=THUMBNAIL)

    def setUp(self):
        self.output = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.output)

    def path(self, *parts):
        return os.path.join(self.output, *parts)

    def data(self, *parts):
        with open(self.path("library", *parts), encoding="utf-8") as f:
            return json.load(f)

    def api(self, name, params=None, **kwargs):
        response = self.client.get(
            reverse(f"kolibri:core:{name}", kwargs=kwargs), params
        )
        self.assertEqual(response.status_code, 200)
        return response.json()


class ExportLibraryDataTestCase(StaticLibraryTestCase):
    def setUp(self):
        super().setUp()
        export_library_data(self.output, available_channels())

    def test_writes_each_node_as_the_api_returns_it(self):
        ids = ContentNode.objects.filter(available=True).values_list("id", flat=True)
        self.assertTrue(ids)
        for node_id in ids:
            self.assertEqual(
                self.data("nodes", f"{node_id}.json"),
                self.api("contentnode-detail", pk=node_id),
            )

    def test_writes_each_topics_children_as_the_api_lists_them(self):
        parents = (
            ContentNode.objects.filter(available=True, parent__isnull=False)
            .values_list("parent_id", flat=True)
            .distinct()
        )
        for parent in parents:
            self.assertEqual(
                self.data("children", f"{parent}.json"),
                self.api("contentnode-list", {"parent": parent}),
            )

    def test_writes_the_channels_as_the_api_lists_them(self):
        channels = self.api("channel-list", {"available": True})
        for channel in channels:
            channel["thumbnail"] = f"/library/channel-thumbnails/{channel['id']}.png"
        self.assertEqual(self.data("channels.json"), channels)

    def test_writes_channel_thumbnails_as_files(self):
        with open(
            self.path("library", "channel-thumbnails", f"{CHANNEL_ID}.png"), "rb"
        ) as f:
            self.assertEqual(f.read(), urlsafe_b64decode(THUMBNAIL.split(",")[1]))

    def test_indexes_each_nodes_fields_to_filter_on(self):
        index = self.data("index", f"{CHANNEL_ID}.json")
        self.assertEqual(index["fields"], list(INDEX_FIELDS))
        rows = {row[0]: dict(zip(INDEX_FIELDS, row)) for row in index["rows"]}
        self.assertEqual(
            set(rows),
            set(
                ContentNode.objects.filter(
                    channel_id=CHANNEL_ID, available=True
                ).values_list("id", flat=True)
            ),
        )
        for node_id, row in rows.items():
            node = self.data("nodes", f"{node_id}.json")
            self.assertEqual(row["title"], node["title"])
            self.assertEqual(row["lft"], node["lft"])
            self.assertEqual(row["learning_activities"], node["learning_activities"])
            self.assertEqual(row["lang_id"], node["lang"] and node["lang"]["id"])
            self.assertFalse(row["in_course"])

    def test_summarizes_the_library_as_the_api_does(self):
        summary = self.data("library.json")
        first_page = self.api("contentnode-list", {"max_results": 25})
        self.assertEqual(summary["labels"], first_page["labels"])
        self.assertEqual(
            summary["first_nodes"], [node["id"] for node in first_page["results"]]
        )
        self.assertEqual(
            summary["count"], ContentNode.objects.filter(available=True).count()
        )
        channel = ChannelMetadata.objects.get(id=CHANNEL_ID)
        self.assertEqual(
            summary["channels"],
            [
                {
                    "id": CHANNEL_ID,
                    "root": channel.root_id,
                    "tree_id": channel.root.tree_id,
                }
            ],
        )


class ExportChosenChannelsTestCase(StaticLibraryTestCase):
    def test_only_writes_chosen_channels(self):
        export_library_data(self.output, available_channels(["f" * 32]))

        self.assertEqual(self.data("channels.json"), [])
        self.assertEqual(self.data("library.json")["count"], 0)
        self.assertFalse(os.path.exists(self.path("library", "nodes")))


class ExportContentTestCase(StaticLibraryTestCase):
    def setUp(self):
        super().setUp()
        self.content_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.content_dir)
        option = override_option("Paths", "CONTENT_FALLBACK_DIRS", [self.content_dir])
        option.enable()
        self.addCleanup(option.disable)
        node = ContentNode.objects.filter(
            channel_id=CHANNEL_ID, available=True
        ).exclude(kind="topic")[0]
        self.archive = self.add_file(node, "a" * 32, "zip")
        self.video = self.add_file(node, "b" * 32, "mp4")

    def add_file(self, node, checksum, extension):
        name = f"{checksum}.{extension}"
        folder = os.path.join(self.content_dir, "storage", name[0], name[1])
        os.makedirs(folder, exist_ok=True)
        if extension == "zip":
            with zipfile.ZipFile(os.path.join(folder, name), "w") as archive:
                archive.writestr("index.html", "<html><body>Equations</body></html>")
        else:
            with open(os.path.join(folder, name), "wb") as f:
                f.write(b"video")
        local_file = LocalFile.objects.create(
            id=checksum, extension=extension, available=True
        )
        File.objects.create(id=checksum, local_file=local_file, contentnode=node)
        return local_file

    def test_writes_content_files_where_their_urls_point(self):
        export_content(self.output, available_channels())

        with open(
            self.path("content", "storage", "b", "b", "b" * 32 + ".mp4"), "rb"
        ) as f:
            self.assertEqual(f.read(), b"video")

    def test_unzips_archives(self):
        export_content(self.output, available_channels())

        self.assertTrue(
            os.path.isfile(
                self.path("content", "zipcontent", "a" * 32 + ".zip", "index.html")
            )
        )

    def test_leaves_out_other_channels_content(self):
        export_content(self.output, available_channels(["f" * 32]))

        self.assertFalse(os.path.exists(self.path("content", "storage", "b")))


class ExportPageTestCase(StaticLibraryTestCase):
    def test_writes_static_files_where_their_urls_point(self):
        path, storage = next(
            found for finder in finders.get_finders() for found in finder.list([])
        )
        export_static_files(self.output)

        with open(self.path("static", path), "rb") as copy, storage.open(
            path
        ) as original:
            self.assertEqual(copy.read(), original.read())

    @patch.object(WebpackBundleHook, "bundle", property(built_bundle))
    def test_writes_the_page_without_other_plugins_navigation(self):
        export_page(self.output)

        with open(self.path("index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('data-plugin="kolibri.plugins.static_library.app"', page)
        self.assertIn('"libraryDataUrl":"/library/"', page)
        self.assertIn("/static/kolibri.core.default_frontend.js", page)
        self.assertIn("/static/kolibri.plugins.static_library.app.js", page)
        self.assertNotIn("side_nav", page)


class ExportCommandTestCase(StaticLibraryTestCase):
    @patch.object(WebpackBundleHook, "bundle", property(built_bundle))
    def test_writes_the_library(self):
        stdout = StringIO()
        call_command("exportstaticlibrary", self.output, stdout=stdout)

        self.assertTrue(os.path.isfile(self.path("index.html")))
        self.assertTrue(os.path.isfile(self.path("library", "library.json")))
        self.assertIn("open /", stdout.getvalue())

    def test_refuses_a_channel_that_is_not_available(self):
        with self.assertRaises(CommandError):
            call_command("exportstaticlibrary", self.output, "--channel", "f" * 32)

    @override_settings(DEVELOPER_MODE=True)
    def test_refuses_a_development_build(self):
        with self.assertRaises(CommandError):
            call_command("exportstaticlibrary", self.output)
