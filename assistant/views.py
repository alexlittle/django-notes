import json
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse

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

        return HttpResponse(response)


class TestStreamView(TemplateView):

    template_name = 'assistant/stream.html'
    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_chat()
        response = na.query_stream(question)

        return StreamingHttpResponse(response, content_type='text/plain')

class HistoryView(TemplateView):
    def get(self, request):
        return render(request,
                      'assistant/history.html')