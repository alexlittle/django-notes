from django.urls import path

from assistant import views

app_name = 'assistant'
urlpatterns = [
    path('', views.HomeView.as_view(), name="home"),
    path('intro', views.ChatIntroView.as_view(), name="chatintro"),
    path('stream', views.TestStreamView.as_view(), name="chatstream"),
    path('history/', views.HistoryView.as_view(), name="history")
    ]