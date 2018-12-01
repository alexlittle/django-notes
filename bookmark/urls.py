# bookmark/urls.py
from django.conf.urls import url

from bookmark import views as bookmark_views

urlpatterns = [
    url(r'^$', bookmark_views.home_view, name="bookmark_home"),
    url(r'^add/$', bookmark_views.add_bookmark, name="bookmark_add"),
    url(r'^edit/(?P<bookmark_id>\d+)/$', bookmark_views.edit_bookmark, name="bookmark_edit"),
    url(r'^tag/(?P<tag_slug>\w[\w/-]*)$', bookmark_views.tag_view, name="tag_view"),
    url(r'^search/$', bookmark_views.search_view, name="bookmark_search"),
]