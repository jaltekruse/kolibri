import os
import shutil
import tempfile
import zipfile

from django.test import TestCase

from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.paths import get_sandbox_html_filename
from kolibri.core.content.utils.static_content import archive_files
from kolibri.core.content.utils.static_content import export_sandbox_static
from kolibri.core.content.utils.static_content import export_zip_content
from kolibri.core.content.zip_wsgi import INITIALIZE_SANDBOX_FROM_IFRAME
from kolibri.utils.tests.helpers import override_option

APP_JS = b"document.body.dataset.ready = 'yes';"
INDEX_HTML = (
    b"<!DOCTYPE html><html><head><title>Equations</title></head><body></body></html>"
)


def write_archive(content_dir, checksum, extension, entries):
    name = f"{checksum}.{extension}"
    folder = os.path.join(content_dir, "storage", name[0], name[1])
    os.makedirs(folder, exist_ok=True)
    with zipfile.ZipFile(os.path.join(folder, name), "w") as archive:
        for entry, data in entries.items():
            archive.writestr(entry, data)
    return LocalFile.objects.create(id=checksum, extension=extension, available=True)


class StaticContentTestCase(TestCase):
    def setUp(self):
        self.content_dir = self._temporary_folder()
        self.static_dir = self._temporary_folder()
        option = override_option("Paths", "CONTENT_FALLBACK_DIRS", [self.content_dir])
        option.enable()
        self.addCleanup(option.disable)
        self.app = write_archive(
            self.content_dir,
            "a" * 32,
            "zip",
            {
                "index.html": INDEX_HTML,
                "js/app.js": APP_JS,
                "../outside.html": INDEX_HTML,
                "/root.js": APP_JS,
            },
        )

    def _temporary_folder(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        return folder

    def unzipped(self, *path):
        return os.path.join(self.static_dir, "zipcontent", "a" * 32 + ".zip", *path)

    def read(self, path):
        with open(path, "rb") as f:
            return f.read()

    def test_unzips_archives_as_kolibri_serves_them(self):
        export_zip_content(archive_files(), self.static_dir)

        self.assertEqual(self.read(self.unzipped("js", "app.js")), APP_JS)
        html = self.read(self.unzipped("index.html")).decode()
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn(INITIALIZE_SANDBOX_FROM_IFRAME, html)

    def test_keeps_entries_inside_the_archive_folder(self):
        export_zip_content(archive_files(), self.static_dir)

        self.assertEqual(
            sorted(os.listdir(os.path.join(self.static_dir, "zipcontent"))),
            ["a" * 32 + ".zip"],
        )
        self.assertEqual(sorted(os.listdir(self.unzipped())), ["index.html", "js"])

    def test_unzips_each_archive_once(self):
        export_zip_content(archive_files(), self.static_dir)
        with open(self.unzipped("js", "app.js"), "wb") as f:
            f.write(b"served already")

        export_zip_content(archive_files(), self.static_dir)

        self.assertEqual(self.read(self.unzipped("js", "app.js")), b"served already")

    def test_only_unzips_available_archives(self):
        LocalFile.objects.create(id="b" * 32, extension="mp4", available=True)
        write_archive(self.content_dir, "c" * 32, "zip", {"index.html": INDEX_HTML})
        LocalFile.objects.filter(id="c" * 32).update(available=False)

        self.assertEqual(list(archive_files()), [self.app])

    def test_only_unzips_a_channels_archives(self):
        self.assertEqual(list(archive_files(channel_id="f" * 32)), [])

    def test_copies_the_sandbox(self):
        export_sandbox_static(self.static_dir)

        sandbox = os.path.join(
            self.static_dir, "static", "sandbox", get_sandbox_html_filename()
        )
        self.assertTrue(os.path.isfile(sandbox))
