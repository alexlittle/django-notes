import json
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import HttpResponse

from assistant.forms import AskForm
from assistant.airag import NotesAssistant

from assistant.models import ChatLog

class HomeView(TemplateView):

    def get(self, request):
        form = AskForm()
        return render(request,
                      'assistant/query.html',
                      {'form': form})

    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_chat()
        response = na.query(question)
        print(f"the response is {response}")
        log = ChatLog()
        log.user = request.user
        log.query = question
        log.response = response
        log.save()

        return HttpResponse(response)

class ChatIntroView(TemplateView):

    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_chat()
        response = na.intro(question)
        print(f"the response is {response}")

        return HttpResponse(response)

class HistoryView(TemplateView):
    def get(self, request):
        return render(request,
                      'assistant/history.html')