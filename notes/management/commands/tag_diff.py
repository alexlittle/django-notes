import difflib

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from notes.models import Tag


class Command(BaseCommand):
    help = _(u"Check for tags that are very similar")
    errors = []

    def handle(self, *args, **options):

        # get all tags as plain list
        tags = list(Tag.objects.order_by('name').values_list('name', flat=True))

        for current_tag in tags:

            filtered_list = [tag for tag in tags if tag != current_tag]
            matches = difflib.get_close_matches(current_tag, filtered_list, cutoff=0.7)
            if matches:
                print(current_tag)
                print(matches)
                print("----------------")