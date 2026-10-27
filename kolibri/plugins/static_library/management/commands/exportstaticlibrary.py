from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from kolibri.plugins.static_library.export import available_channels
from kolibri.plugins.static_library.export import export_library
from kolibri.plugins.static_library.paths import library_page_url


class Command(BaseCommand):
    help = (
        "Writes the library as files a static web host can serve: a page to browse "
        "and search the channels and use their resources, as a guest does in Learn, "
        "and the content and data it needs. Serve OUTPUT as the site's root; the "
        "page is at URL_PATH_PREFIX, and content at ZIP_CONTENT_URL_PATH_PREFIX, as "
        "on this Kolibri. Needs a production build of the frontend."
    )

    def add_arguments(self, parser):
        parser.add_argument("output", help="Folder to write the library into")
        parser.add_argument(
            "--channel",
            dest="channel_ids",
            action="append",
            metavar="CHANNEL_ID",
            help="Only export this channel; repeat for more. Defaults to every available channel.",
        )

    def handle(self, output, channel_ids, **options):
        if getattr(settings, "DEVELOPER_MODE", False):
            raise CommandError(
                "The page would load its code from the development server; "
                "run with production settings and a production build."
            )
        missing = set(channel_ids or []) - set(
            available_channels(channel_ids).values_list("id", flat=True)
        )
        if missing:
            raise CommandError(f"No available channel {', '.join(sorted(missing))}")
        export_library(output, channel_ids)
        self.stdout.write(f"Serve {output} and open {library_page_url()}")
