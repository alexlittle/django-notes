"""
Removes unused tags
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from notes.models import INACTIVE_NOTE_STATUSES, Tag


class Command(BaseCommand):
    help = _("Cleans unused tags and flags any that are only used once")
    errors = []

    def handle(self, *args, **options):
        # Matches Tag.note_count()'s definition of "used": a note in one of
        # INACTIVE_NOTE_STATUSES doesn't count, so a tag whose only notes
        # are e.g. archived is still "unused" here.
        tags = Tag.objects.filter(favourite=False).annotate(
            note_count=Count(
                "notetag__note__id",
                filter=~Q(notetag__note__status__in=INACTIVE_NOTE_STATUSES),
            )
        )

        unused_tags = tags.filter(note_count=0)
        for tag in unused_tags:
            print(tag.name + ": deleted")
            tag.delete()
