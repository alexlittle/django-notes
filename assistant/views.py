from django.views.generic import TemplateView
from django.shortcuts import render



class HomeView(TemplateView):
    def get(self, request):
        return render(request,
                      'assistant/query.html')


class HistoryView(TemplateView):
    def get(self, request):
        return render(request,
                      'assistant/history.html')