from kolibri.core.content.constants.schema_versions import CONTENT_SCHEMA_VERSION
from kolibri.core.content.hooks import ChannelImportHook
from kolibri.core.content.models import ChannelMetadata
from kolibri.core.content.test.test_channel_import import ContentImportTestBase
from kolibri.plugins.hooks import register_hook

# The channel in the content fixture
CHANNEL_ID = "6199dde695db4ee4ab392222d5af1e5c"


class ChannelImportHookTestCase(ContentImportTestBase):
    """Plugins hear of each import that replaces a channel's content."""

    name = CONTENT_SCHEMA_VERSION
    legacy_schema = None

    def setUp(self):
        registered_hooks = ChannelImportHook._registered_hooks
        ChannelImportHook._registered_hooks = {}
        self.addCleanup(
            setattr, ChannelImportHook, "_registered_hooks", registered_hooks
        )
        self.imported = imported = []

        class RecordingHook(ChannelImportHook):
            def channel_imported(self, channel_id):
                imported.append(channel_id)

        RecordingHook.__module__ = "test.kolibri_plugin"
        register_hook(RecordingHook).add_hook_to_registries()
        # Imports the channel
        super().setUp()

    def test_hears_of_a_new_channel(self):
        self.assertEqual(self.imported, [CHANNEL_ID])

    def test_hears_of_a_new_version_of_a_channel(self):
        channel = ChannelMetadata.objects.get(id=CHANNEL_ID)
        channel.version -= 1
        channel.save()

        self.set_content_fixture()

        self.assertEqual(self.imported, [CHANNEL_ID, CHANNEL_ID])

    def test_does_not_hear_of_a_version_it_already_has(self):
        self.set_content_fixture()

        self.assertEqual(self.imported, [CHANNEL_ID])
