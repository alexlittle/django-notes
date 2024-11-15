from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.translation import gettext_lazy as _
from assistant.airag import NotesAssistant

from notes.models import Note


class Command(BaseCommand):
    help = _(u"Rebuilds the vector store")
    errors = []

    def handle(self, *args, **options):
        # delete the collection
        na = NotesAssistant()
        vs = na.get_vs()
        vs.delete_collection()

        # reset all captured notes
        notes = Note.objects.filter(assistant_loaded=True)
        for n in notes:
            n.assistant_loaded = False
            n.save()

        # rebuild vector store
        call_command('repopulate_vs')