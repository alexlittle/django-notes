from django.urls import path

from assistant import views

app_name = 'assistant'
urlpatterns = [
    path('', views.ChatView.as_view(), name="home"),
    path('stream', views.ChatStreamView.as_view(), name="chatstream"),
    path('intro', views.ChatIntroView.as_view(), name="chatintro"),
    path('stream/intro', views.ChatIntroStreamView.as_view(), name="chatintrostream"),
    path('history/', views.HistoryView.as_view(), name="history")
    ]