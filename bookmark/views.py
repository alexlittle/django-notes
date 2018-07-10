from django.shortcuts import render

from bookmark.models import Bookmark

def home_view(request):
    bookmarks = Bookmark.objects.all()
    return render(request, 'bookmark/home.html',
                          {'bookmarks': bookmarks})