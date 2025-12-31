from django.urls import path
from django.contrib.auth.views import LoginView

from notes import views as note_views

app_name = 'notes'
urlpatterns = [
    path('', note_views.HomeView.as_view(), name="home"),
    path('login/', LoginView.as_view(template_name='notes/login.html'), name='login'),
    path('recent/', note_views.RecentView.as_view(), name="recent"),
    path('tasks/', note_views.TasksView.as_view(), name="tasks"),
    path('tasks/tags/', note_views.TasksTagsView.as_view(), name="tasks_tags_home"),
    path('tasks/future/', note_views.FutureTasksView.as_view(), name="tasks_future"),
    path('tasks/tags/<tag_slug>/', note_views.TagTasksView.as_view(), name="tag_tasks"),
    path('bookmarks/', note_views.BookmarksView.as_view(), name="bookmarks"),
    path('ideas/', note_views.IdeasView.as_view(), name="ideas"),
    path('task/<int:note_id>/complete', note_views.CompleteTaskView.as_view(), name="complete_task"),
    path('task/<int:note_id>/uncomplete', note_views.UnCompleteTaskView.as_view(), name="uncomplete_task"),
    path('task/<int:note_id>/close', note_views.CloseTaskView.as_view(), name="close_task"),
    path('add/', note_views.AddView.as_view(), name="add"),
    path('edit/<int:note_id>/', note_views.EditView.as_view(), name="edit"),
    path('tags/', note_views.TagsView.as_view(), name="tags"),
    path('tag/<tag_slug>/', note_views.TagView.as_view(), name="tag_view"),
    path('api/autocomplete/', note_views.TagAutocompleteView.as_view(), name='tag-autocomplete'),
    path('search/', note_views.SearchView.as_view(), name="search"),
    path('fav/', note_views.FavouritesView.as_view(), name="favs"),

    path('weeklyschedule/', note_views.WeeklyScheduleView.as_view(), name="weeklyschedule"),
]
