from django.urls import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView

from bookmark.forms import BookmarkForm, SearchForm
from bookmark.models import Bookmark, Tag, BookmarkTag
from haystack.query import SearchQuerySet


class HomeView(TemplateView):

    def get(self, request):

        bmarks = Bookmark.objects.all().order_by('-create_date')

        paginator = Paginator(bmarks, 50)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            bookmarks = paginator.page(page)
        except (EmptyPage, InvalidPage):
            bookmarks = paginator.page(paginator.num_pages)

        return render(request,
                      'bookmark/home.html',
                      {'page': bookmarks})


class AddView(TemplateView):
    def get(self, request):
        form = BookmarkForm()
        return render(request,
                      'bookmark/form.html',
                      {'form': form})

    def post(self, request):
        form = BookmarkForm(request.POST)
        if form.is_valid():
            bookmark = Bookmark()
            bookmark.title = form.cleaned_data.get("title")
            bookmark.description = form.cleaned_data.get("description")
            bookmark.url = form.cleaned_data.get("url")
            bookmark.save()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                bookmark_tag, created = \
                    BookmarkTag.objects.get_or_create(bookmark=bookmark,
                                                      tag=tag)
        return HttpResponseRedirect(reverse('bookmark:home'))


class EditView(TemplateView):
    def get(self, request, bookmark_id):
        bookmark = Bookmark.objects.get(pk=bookmark_id)
        tags = Tag.objects.filter(bookmarktag__bookmark=bookmark) \
            .values_list('name', flat=True)
        data = {}
        data['tags'] = ", ".join(tags)
        data['title'] = bookmark.title
        data['description'] = bookmark.description
        data['url'] = bookmark.url
        form = BookmarkForm(initial=data)
        return render(request,
                      'bookmark/form.html',
                      {'form': form})

    def post(self, request, bookmark_id):
        bookmark = Bookmark.objects.get(pk=bookmark_id)
        form = BookmarkForm(request.POST)
        if form.is_valid():
            BookmarkTag.objects.filter(bookmark=bookmark).delete()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                bookmark_tag, created = BookmarkTag.objects \
                    .get_or_create(bookmark=bookmark, tag=tag)
            bookmark.title = form.cleaned_data.get("title")
            bookmark.url = form.cleaned_data.get("url")
            bookmark.description = form.cleaned_data.get("description")
            bookmark.save()
        return HttpResponseRedirect(reverse('bookmark:home'))


class TagView(TemplateView):
    def get(self, request, tag_slug):
        tag = Tag.objects.get(slug=tag_slug)
        bookmarks = Bookmark.objects.filter(bookmarktag__tag=tag)
        return render(request,
                      'bookmark/tag.html',
                      {'tag': tag,
                       'bookmarks': bookmarks})


class SearchView(TemplateView):
    def get(self, request):
        search_query = request.GET.get('q', '')

        if search_query:
            search_results = SearchQuerySet().filter(content=search_query)
        else:
            search_results = []

        data = {}
        data['q'] = search_query
        form = SearchForm(initial=data)

        paginator = Paginator(search_results, 50)
        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            results = paginator.page(page)
        except (EmptyPage, InvalidPage):
            results = paginator.page(paginator.num_pages)

        return render(request, 'bookmark/search.html', {
            'form': form,
            'query': search_query,
            'page': results,
            'total_results': paginator.count,
        })


class FavouritesView(TemplateView):
    def get(self, request):
        tags = Tag.objects.filter(favourite=True)

        return render(request,
                      'bookmark/fav.html',
                      {'tags': tags})


class TagsView(TemplateView):
    
    def get(self, request):
        tags = Tag.objects.all().order_by('-favourite', 'name')

        paginator = Paginator(tags, 50)
        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            results = paginator.page(page)
        except (EmptyPage, InvalidPage):
            results = paginator.page(paginator.num_pages)

        return render(request,
                      'bookmark/tags.html',
                      {'page': results})
