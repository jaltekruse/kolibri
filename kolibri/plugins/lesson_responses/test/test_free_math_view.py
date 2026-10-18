import os
import tempfile
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from kolibri.core.auth.test.helpers import provision_device
from kolibri.plugins.lesson_responses.vendor_free_math import make_embed_html

URL_NAME = "kolibri:kolibri.plugins.lesson_responses:free_math"


class FreeMathViewTestCase(TestCase):
    databases = "__all__"

    def setUp(self):
        provision_device()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.embed_html = os.path.join(self.temp_dir.name, "embed.html")
        with open(self.embed_html, "w") as f:
            f.write('<html><head><script src="lib/jquery.js"></script></head></html>')

    def tearDown(self):
        self.temp_dir.cleanup()

    def _get(self, found_path):
        with mock.patch(
            "kolibri.plugins.lesson_responses.views.finders.find",
            return_value=found_path,
        ):
            return self.client.get(reverse(URL_NAME), {"embedded": "student"})

    def test_serves_free_math_with_links_relative_to_its_static_files(self):
        response = self._get(self.embed_html)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, '<head><base href="/static/lesson_responses/free_math/">'
        )

    def test_can_be_framed_by_kolibri_pages_only(self):
        response = self._get(self.embed_html)
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")

    def test_allows_scripts_to_compile_code(self):
        response = self._get(self.embed_html)
        script_src = next(
            directive
            for directive in response["Content-Security-Policy"].split(";")
            if directive.strip().startswith("script-src")
        )
        self.assertIn("'unsafe-eval'", script_src)

    def test_not_found_when_free_math_is_not_installed(self):
        response = self._get(None)
        self.assertEqual(response.status_code, 404)


def test_embed_html_drops_inline_and_remote_scripts():
    index_html = (
        "<html><head>"
        '<script async src="https://www.googletagmanager.com/gtag/js"></script>'
        "<script>window.dataLayer = [];</script>"
        '<link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet">'
        '<script src="lib/jquery.js"></script>'
        '<link rel="stylesheet" href="katex.min.css">'
        "</head><body></body></html>"
    )
    assert make_embed_html(index_html) == (
        "<html><head>"
        '<script src="lib/jquery.js"></script>'
        '<link rel="stylesheet" href="katex.min.css">'
        "</head><body></body></html>"
    )
