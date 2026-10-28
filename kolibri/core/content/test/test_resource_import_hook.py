import hashlib
import os
import shutil
import tempfile

from django.test import TestCase
from le_utils.constants import content_kinds
from le_utils.constants import format_presets

from kolibri.core.content.hooks import ResourceImportHook
from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.models import ContentNode
from kolibri.core.content.models import File
from kolibri.core.content.models import LocalFile
from kolibri.core.content.utils.content_types_tools import renderable_preset_bits
from kolibri.core.content.utils.paths import get_content_file_name
from kolibri.core.content.utils.paths import get_content_storage_file_path
from kolibri.core.content.utils.resource_import import DiskChannelResourceImportManager
from kolibri.plugins.hooks import register_hook
from kolibri.utils.tests.helpers import override_option

# The channel in the content fixture
CHANNEL_ID = "6199dde695db4ee4ab392222d5af1e5c"
DOCUMENT = b"%PDF-1.4 Equations"
CHECKSUM = hashlib.md5(DOCUMENT).hexdigest()


class ResourceImportHookTestCase(TestCase):
    """Plugins hear of each import of a channel's resources."""

    fixtures = ["content_test.json"]  # noqa: RUF012

    def setUp(self):
        registered_hooks = ResourceImportHook._registered_hooks
        ResourceImportHook._registered_hooks = {}
        self.addCleanup(
            setattr, ResourceImportHook, "_registered_hooks", registered_hooks
        )
        self.heard = heard = []

        class RecordingHook(ResourceImportHook):
            def resources_imported(self, channel_id):
                # Whether the imported file was on the device by then
                available = LocalFile.objects.get(id=CHECKSUM).available
                heard.append((channel_id, available))

        RecordingHook.__module__ = "test.kolibri_plugin"
        register_hook(RecordingHook).add_hook_to_registries()

        option = override_option("Paths", "CONTENT_DIR", self._temporary_folder())
        option.enable()
        self.addCleanup(option.disable)
        self.drive = self._temporary_folder()

        root = ChannelMetadata.objects.get(id=CHANNEL_ID).root
        self.document = ContentNode.objects.create(
            id="d" * 32,
            title="Equations",
            content_id="e" * 32,
            channel_id=CHANNEL_ID,
            parent=root,
            kind=content_kinds.DOCUMENT,
        )
        local_file = LocalFile.objects.create(
            id=CHECKSUM, extension="pdf", file_size=len(DOCUMENT), available=False
        )
        File.objects.create(
            id="f" * 32,
            local_file=local_file,
            contentnode=self.document,
            preset=format_presets.DOCUMENT,
            # As a channel's import sets it, for its viewer
            included_presets=renderable_preset_bits.get(format_presets.DOCUMENT),
        )
        # On the drive the import copies from
        source = get_content_storage_file_path(
            get_content_file_name(local_file), datafolder=self.drive
        )
        os.makedirs(os.path.dirname(source))
        with open(source, "wb") as f:
            f.write(DOCUMENT)

    def _temporary_folder(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        return folder

    def test_hears_of_an_import_once_its_files_are_on_the_device(self):
        DiskChannelResourceImportManager(
            CHANNEL_ID, path=self.drive, node_ids=[self.document.id]
        ).run()

        self.assertEqual(self.heard, [(CHANNEL_ID, True)])
