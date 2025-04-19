import difflib

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from notes.models import Tag


class Command(BaseCommand):
    help = _(u"Check for tags that are very similar")
    errors = []

    def add_arguments(self, parser):
        parser.add_argument('cutoff', type=float, default=0.6, nargs='?')

    def handle(self, *args, **options):

        cutoff = options['cutoff']

        # get all tags as plain list
        tags = list(Tag.objects.order_by('name').values_list('name', flat=True))

        for current_tag in tags:

            filtered_list = [tag for tag in tags if tag != current_tag]
            matches = difflib.get_close_matches(current_tag, filtered_list, cutoff=cutoff)
            if matches:
                print(current_tag)
                print(matches)
                print("----------------")