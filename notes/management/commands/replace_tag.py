from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from notes.models import NoteTag, Tag


class Command(BaseCommand):
    help = _("Replaces tags")
    errors = []

    def add_arguments(self, parser):
        parser.add_argument("oldtag", type=str)
        parser.add_argument("newtag", type=str)

    def handle(self, *args, **options):
        oldtag = Tag.objects.get(slug=options["oldtag"])
        newtag = Tag.objects.get(slug=options["newtag"])

        # add new tag to all notes with the old one
        note_tags = list(NoteTag.objects.filter(tag=oldtag))
        for nt in note_tags:
            if NoteTag.objects.filter(note=nt.note, tag=newtag).exists():
                nt.delete()
            else:
                nt.tag = newtag
                nt.save()

        oldtag.delete()
        print(f"{len(note_tags)} tags replaced {options['oldtag']}")
