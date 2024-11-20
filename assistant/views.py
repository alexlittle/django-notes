import json
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse

from assistant.forms import AskForm
from assistant.airag import NotesAssistant

from assistant.models import ChatLog

class ChatView(TemplateView):

    template_name = 'assistant/chat.html'

    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_chat()
        response = na.query(question)
        return HttpResponse(response)

class ChatStreamView(TemplateView):

    template_name = 'assistant/stream.html'

    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_stream_chat()
        response = na.query_stream(question)
        return StreamingHttpResponse(response, content_type='text/plain')


class ChatIntroView(TemplateView):

    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_chat()
        response = na.intro(question)

        return HttpResponse(response)

class ChatIntroStreamView(TemplateView):

    def post(self, request):
        body = json.loads(request.body)
        question = body['question']
        na = NotesAssistant()
        na.init_stream_chat()
        response = na.intro_stream(question)

        return StreamingHttpResponse(response, content_type='text/plain')

class HistoryView(TemplateView):

    template_name = 'assistant/history.html'