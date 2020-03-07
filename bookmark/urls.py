
from django.urls import path
from django.views.generic import TemplateView

from bookmark import views as bookmark_views

app_name = 'bookmark'
urlpatterns = [
    path('', bookmark_views.HomeView.as_view(), name="home"),
    path('add/', bookmark_views.AddView.as_view(), name="add"),
    path('edit/<int:bookmark_id>/', bookmark_views.EditView.as_view(), name="edit"),
    path('tag/<tag_slug>', bookmark_views.TagView.as_view(), name="tag_view"),
    path('search/', bookmark_views.SearchView.as_view(), name="search"),
    path('fav/', bookmark_views.FavouritesView.as_view(), name="favs"),
]