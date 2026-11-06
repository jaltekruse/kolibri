from kolibri.core.webpack import hooks as webpack_hooks
from kolibri.plugins import KolibriPluginBase
from kolibri.plugins.hooks import register_hook


class QuickAssign(KolibriPluginBase):
    untranslated_view_urls = "api_urls"
    translated_view_urls = "urls"
    root_view_urls = "root_urls"


@register_hook
class QuickAssignAsset(webpack_hooks.WebpackBundleHook):
    bundle_id = "app"
