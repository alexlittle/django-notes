# bookmark/urls.py
from django.conf import settings
from django.conf.urls import include, url

from bookmark import views as bookmark_views

urlpatterns = [
    url(r'^$', bookmark_views.home_view, name="bookmark_home"),
    url(r'^add/$', bookmark_views.add_bookmark, name="bookmark_add"),
    url(r'^edit/(?P<bookmark_id>\d+)/$', bookmark_views.edit_bookmark, name="bookmark_edit"),
]