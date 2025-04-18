'''
Removes unused tags
'''

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.urls import reverse
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
        print("--------------------------")
        used_once_tags = tags.filter(note_count=1).order_by("name")
        for idx, tag in enumerate(used_once_tags):
            url = "http://localhost:9030" + reverse('notes:tag_view', args=[tag.slug])
            print("%d/%d %s: only 1 use : %s" % (idx, used_once_tags.count(), tag.name, url))
