from kolibri.utils import conf

LIBRARY_DATA_FOLDER = "library"


def library_page_url():
    """Where the page is, as Kolibri's own pages start at URL_PATH_PREFIX."""
    return "/" + conf.OPTIONS["Deployment"]["URL_PATH_PREFIX"].lstrip("/")


def library_data_url():
    """Where the JSON the page answers its API requests from is."""
    return f"{library_page_url()}{LIBRARY_DATA_FOLDER}/"
