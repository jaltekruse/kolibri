import posixpath

from django.conf import settings

from kolibri.core.content.utils.paths import get_content_url
from kolibri.core.content.utils.paths import zip_content_path_prefix
from kolibri.utils import conf

LIBRARY_DATA_FOLDER = "library"


def library_page_url():
    """Where the page is, as Kolibri's own pages start at URL_PATH_PREFIX."""
    return "/" + conf.OPTIONS["Deployment"]["URL_PATH_PREFIX"].lstrip("/")


def library_data_url():
    """Where the JSON the page answers its API requests from is."""
    return f"{library_page_url()}{LIBRARY_DATA_FOLDER}/"


def exported_url_roots():
    """
    The URLs the export's files are under, as this Kolibri's: its static files, its
    content and its zip content origin's, and the library's data.
    """
    url_prefix = conf.OPTIONS["Deployment"]["URL_PATH_PREFIX"]
    return {
        settings.STATIC_URL,
        "/" + get_content_url(url_prefix).lstrip("/"),
        "/" + get_content_url(zip_content_path_prefix()).lstrip("/"),
        library_data_url(),
    }


def relative_url(url, folder):
    """
    A URL of the export's, relative to a folder of it, so the export works wherever
    it is served from, as a GitHub Pages project site.
    """
    relative = posixpath.relpath(url, folder)
    return f"{relative}/" if url.endswith("/") else relative
