from django.core.management.base import BaseCommand

from kolibri.plugins.media_player.khan_academy import add_youtube_ids


class Command(BaseCommand):
    help = (
        "Record the YouTube ids of the videos in Khan Academy channels, from Khan "
        "Academy's public content export, so they can play from YouTube. Importing "
        "a Khan Academy channel does this when YouTube playback is on."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "channel_ids",
            nargs="*",
            help="The channels to look in. All channels when none are given.",
        )
        parser.add_argument(
            "--export",
            help="A downloaded export file to read, instead of downloading the "
            "export for each channel's language",
        )

    def handle(self, *args, **options):
        add_youtube_ids(options["channel_ids"], export=options["export"])
