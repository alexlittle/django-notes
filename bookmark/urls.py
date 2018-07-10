# bookmark/urls.py
from django.conf import settings
from django.conf.urls import include, url

from bookmark import views as bookmark_views

urlpatterns = [
    url(r'^$', bookmark_views.home_view, name="bookmark_home"),
]