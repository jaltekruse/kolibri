import json

from django import template
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe

from kolibri.core.webpack.hooks import WebpackBundleHook
from kolibri.plugins.static_library.paths import exported_url_roots
from kolibri.plugins.static_library.paths import library_page_url
from kolibri.plugins.static_library.paths import relative_url

register = template.Library()


def page_urls_script():
    """
    A script resolving the page's URLs, which the export writes relative to it,
    against the page, in the data Kolibri and its plugins read.
    """
    roots = sorted(
        relative_url(root, library_page_url()) for root in exported_url_roots()
    )
    script = render_to_string("static_library/page_urls.js")
    return (
        f'<script data-relative-roots="{escape(json.dumps(roots))}">\n{script}</script>'
    )


@register.simple_tag()
def core_assets_without_navigation():
    """
    The core bundle without other plugins' navigation bundles, as there is no
    Kolibri server behind a static library to open their pages. Its data and the
    content viewers' come before it, so the page's URLs are resolved in them before
    any of Kolibri's scripts read them, whichever loads first.
    """
    core = WebpackBundleHook.get_by_unique_id("kolibri.core.default_frontend")
    html = core.render_to_page_load_sync_html(navigation=False)
    scripts = html.index("<script")
    return mark_safe(html[:scripts] + page_urls_script() + html[scripts:])
