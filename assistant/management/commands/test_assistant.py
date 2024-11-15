from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from assistant.airag import NotesAssistant

class Command(BaseCommand):
    help = _(u"For testing the assistant via the command line")
    errors = []

    def handle(self, *args, **options):
        query = input("Enter your query: ")

        print(f"your query was: '{query}'")

        na = NotesAssistant()
        na.init_chat()

        response = na.query(query)
        print(response)
