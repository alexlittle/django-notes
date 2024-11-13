from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from assistant.airag import NotesAssistant
class Command(BaseCommand):
    help = _(u"Repopulates vector store")
    errors = []

    def handle(self, *args, **options):

        na = NotesAssistant()
        na.pre_populate()

