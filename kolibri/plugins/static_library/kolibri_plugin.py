from kolibri.core.webpack import hooks as webpack_hooks
from kolibri.plugins import KolibriPluginBase
from kolibri.plugins.hooks import register_hook
from kolibri.utils import translation
from kolibri.utils.translation import gettext as _

from .paths import exported_url_roots
from .paths import library_data_url
from .paths import library_page_url
from .paths import relative_url


class StaticLibrary(KolibriPluginBase):
    """
    Exports the library as files a static web host can serve: a page for browsing
    and searching channels and using their resources, as guests do in Learn, which
    answers its API requests from JSON files written alongside it.
    """

    def name(self, lang):
        with translation.override(lang):
            return _("Static library")


@register_hook
class StaticLibraryAsset(webpack_hooks.WebpackBundleHook):
    bundle_id = "app"

    @property
    def plugin_data(self):
        return {
            # Read by Learn's pages, which this page shows to a guest
            "allowDownloadOnMeteredConnection": False,
            "allowGuestAccess": True,
            "allowLearnerDownloads": False,
            "allowLearnerUnassignedResourceAccess": True,
            "allowRemoteAccess": True,
            "canCheckMeteredConnection": False,
            "canShareFile": False,
            "enableCustomChannelNav": False,
            # Relative to the page, as its other URLs are, which the page resolves
            # where Kolibri needs them whole
            "libraryDataUrl": relative_url(library_data_url(), library_page_url()),
            "relativeRoots": sorted(
                relative_url(root, library_page_url()) for root in exported_url_roots()
            ),
        }
