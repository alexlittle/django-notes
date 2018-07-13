from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from bookmark.forms import BookmarkForm
from bookmark.models import Bookmark, Tag, BookmarkTag

def home_view(request):
    bookmarks = Bookmark.objects.all().order_by('-create_date')
    return render(request, 'bookmark/home.html',
                          {'bookmarks': bookmarks})
    
def add_bookmark(request):
    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        if form.is_valid(): # All validation rules pass
            bookmark = Bookmark()
            bookmark.title = form.cleaned_data.get("title")
            bookmark.url = form.cleaned_data.get("url")
            bookmark.save()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                bookmark_tag, created = BookmarkTag.objects.get_or_create(bookmark=bookmark, tag= tag)
        return HttpResponseRedirect(reverse('bookmark_home'))
     
    else:

        form = BookmarkForm()
    return render(request, 'bookmark/form.html',
                          {'form': form})
    
def edit_bookmark(request, bookmark_id):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    
    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        if form.is_valid(): # All validation rules pass
            # delete any existing tags
            BookmarkTag.objects.filter(bookmark=bookmark).delete()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                bookmark_tag, created = BookmarkTag.objects.get_or_create(bookmark=bookmark, tag= tag)
            bookmark.title = form.cleaned_data.get("title")
            bookmark.url = form.cleaned_data.get("url")
            bookmark.save()   
        return HttpResponseRedirect(reverse('bookmark_home'))
     
    else:
        tags = Tag.objects.filter(bookmarktag__bookmark=bookmark).values_list('name', flat=True)
        data = {}
        data['tags'] = ", ".join(tags)
        data['title'] = bookmark.title
        data['url'] = bookmark.url
        form = BookmarkForm(initial=data)
    return render(request, 'bookmark/form.html',
                          {'form': form})   