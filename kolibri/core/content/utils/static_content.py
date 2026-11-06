"""
Kolibri's zip content origin as plain files, so a static web server, or a bucket
behind a CDN, can serve it instead of Kolibri. Kolibri's own server for that origin
opens archives (HTML5 apps, H5P and the like) on every request; here they are
unzipped once, into folders laid out like that origin's URLs:

    <dir>/zipcontent/<checksum>.<extension>/<file in the archive>
    <dir>/static/<sandbox files, such as sandbox/sandbox-<hash>.html>

Serve <dir> at the origin's content/ path, under ZIP_CONTENT_URL_PATH_PREFIX.
"""

import logging
import os
import posixpath
import shutil
import tempfile
import zipfile

from kolibri.core.content.hooks import SandboxedContentViewerHook
from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.paths import get_content_file_name
from kolibri.core.content.utils.paths import get_content_storage_file_path
from kolibri.core.content.zip_wsgi import archive_file_types
from kolibri.core.content.zip_wsgi import parse_html

logger = logging.getLogger(__name__)

ZIP_CONTENT_FOLDER = "zipcontent"
SANDBOX_FOLDER = "static"


def archive_files(channel_id=None):
    """The available archive files Kolibri serves on its zip content origin."""
    local_files = LocalFile.objects.filter(
        available=True, extension__in=archive_file_types
    )
    if channel_id is not None:
        local_files = local_files.filter(files__contentnode__channel_id=channel_id)
    return local_files.distinct()


def _is_html(path):
    # As Kolibri's zip content server decides which files to add its script to
    return path.lower().endswith(("html", "htm"))


def _safe_path(name):
    """
    The path an archive entry unzips to, or None for folders and for entries that
    would land outside the archive's folder.
    """
    path = posixpath.normpath(name)
    if name.endswith("/") or path in (".", "..") or path.startswith(("/", "../")):
        return None
    return path


def _unzip(zip_path, folder):
    with zipfile.ZipFile(zip_path) as archive:
        for entry in archive.infolist():
            path = _safe_path(entry.filename)
            if path is None:
                continue
            target = os.path.join(folder, *path.split("/"))
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
            except (FileExistsError, NotADirectoryError):
                # An entry also used as a folder, which only one of can be on disk
                logger.warning("Skipping %s in %s", entry.filename, zip_path)
                continue
            with archive.open(entry) as source, open(target, "wb") as destination:
                if _is_html(path):
                    html = parse_html(source.read())
                    destination.write(html.encode() if isinstance(html, str) else html)
                else:
                    shutil.copyfileobj(source, destination)


def export_zip_content(local_files, root):
    """
    Unzips each archive into root, once: archives are named by checksum, so a
    folder that exists already holds the same files.
    """
    folder = os.path.join(root, ZIP_CONTENT_FOLDER)
    os.makedirs(folder, exist_ok=True)
    for local_file in local_files:
        filename = get_content_file_name(local_file)
        destination = os.path.join(folder, filename)
        if os.path.exists(destination):
            continue
        # Unzip beside the destination, then move it in whole, so a server never
        # sees a partly unzipped archive
        temporary = tempfile.mkdtemp(prefix=f".{filename}.", dir=folder)
        try:
            os.chmod(temporary, 0o755)
            _unzip(get_content_storage_file_path(filename), temporary)
            try:
                os.rename(temporary, destination)
            except OSError:
                # Unzipped by another process meanwhile
                if not os.path.isdir(destination):
                    raise
        finally:
            shutil.rmtree(temporary, ignore_errors=True)


def export_sandbox_static(root):
    """
    Copies the files of the sandbox that frames content, which Kolibri serves on its
    zip content origin too. The first sandbox folder holding a path wins, as in
    Kolibri, so they are copied last to first. Viewers with nothing built yet have
    no folder.
    """
    destination = os.path.join(root, SANDBOX_FOLDER)
    for folder in reversed(SandboxedContentViewerHook.get_sandbox_static_paths()):
        if os.path.isdir(folder):
            shutil.copytree(folder, destination, dirs_exist_ok=True)
