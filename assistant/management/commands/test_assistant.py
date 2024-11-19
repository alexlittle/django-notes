from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from assistant.airag import NotesAssistant

class Command(BaseCommand):
    help = _(u"For testing the assistant via the command line")
    errors = []

    def handle(self, *args, **options):
        '''
        from langchain import hub
        prompt = hub.pull("rlm/rag-prompt")
        print(prompt)
        return
        '''

        query = input("Enter your query: ")

        print(f"your query was: '{query}'")

        na = NotesAssistant()
        na.init_chat()

        for chunk in na.query_stream(query):
            print(chunk)
