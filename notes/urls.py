from django.urls import path

from notes import views as note_views

app_name = 'notes'
urlpatterns = [
    path('', note_views.HomeView.as_view(), name="home"),
    path('tasks/', note_views.TasksView.as_view(), name="tasks"),
    path('tasks/tags/', note_views.TasksTagsView.as_view(), name="tasks_tags_home"),
    path('tasks/tags/<tag_slug>/', note_views.TagTasksView.as_view(), name="tag_tasks"),
    path('notes/', note_views.NotesView.as_view(), name="notes"),
    path('task/<int:note_id>/complete', note_views.CompleteTaskView.as_view(), name="complete_task"),
    path('add/', note_views.AddView.as_view(), name="add"),
    path('edit/<int:note_id>/', note_views.EditView.as_view(), name="edit"),
    path('tags/', note_views.TagsView.as_view(), name="tags"),
    path('tag/<tag_slug>/', note_views.TagView.as_view(), name="tag_view"),
    path('search/', note_views.SearchView.as_view(), name="search"),
    path('fav/', note_views.FavouritesView.as_view(), name="favs"),
]
