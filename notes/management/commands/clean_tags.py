'''
Removes unused tags
'''

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from notes.models import Tag


class Command(BaseCommand):
    help = _(u"Cleans unused tags and flags any that are only used once")
    errors = []

    def handle(self, *args, **options):
        tags = Tag.objects.filter(favourite=False).annotate(note_count=Count("notetag__note__id"))

        unused_tags = tags.filter(note_count=0)
        for tag in unused_tags:
            print(tag.name + ": deleted")
            tag.delete()
