
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from notes.models import Tag, NoteTag


class Command(BaseCommand):
    help = _(u"Replaces tags")
    errors = []

    def add_arguments(self, parser):
        parser.add_argument('oldtag', type=str)
        parser.add_argument('newtag', type=str)

    def handle(self, *args, **options):
        oldtag = Tag.objects.get(slug=options['oldtag'])
        newtag = Tag.objects.get(slug=options['newtag'])

        # add new tag to all notes with the old one
        note_tags = NoteTag.objects.filter(tag=oldtag)
        for nt in note_tags:
            new_nt = NoteTag()
            new_nt.note = nt.note
            new_nt.tag = newtag
            new_nt.save()
            nt.delete()

