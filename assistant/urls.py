from django.urls import path

from assistant import views

app_name = 'assistant'
urlpatterns = [
    path('', views.HomeView.as_view(), name="home"),
    path('history/', views.HistoryView.as_view(), name="history")
    ]