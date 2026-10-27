from django import template

from kolibri.core.webpack.hooks import WebpackBundleHook

register = template.Library()


@register.simple_tag()
def core_assets_without_navigation():
    """
    The core bundle without other plugins' navigation bundles, as there is no
    Kolibri server behind a static library to open their pages.
    """
    core = WebpackBundleHook.get_by_unique_id("kolibri.core.default_frontend")
    return core.render_to_page_load_sync_html(navigation=False)
