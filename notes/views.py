from django.urls import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView

from notes.forms import NoteForm, SearchForm
from notes.models import Note, Tag, NoteTag
from haystack.query import SearchQuerySet


class HomeView(TemplateView):

    def get(self, request):

        bmarks = Note.objects.all().order_by('-create_date')

        paginator = Paginator(bmarks, 50)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            notes = paginator.page(page)
        except (EmptyPage, InvalidPage):
            notes = paginator.page(paginator.num_pages)

        return render(request,
                      'notes/home.html',
                      {'page': notes})


class AddView(TemplateView):
    def get(self, request):
        form = NoteForm()
        return render(request,
                      'notes/form.html',
                      {'form': form})

    def post(self, request):
        form = NoteForm(request.POST)
        if form.is_valid():
            note = Note()
            note.title = form.cleaned_data.get("title")
            note.description = form.cleaned_data.get("description")
            note.url = form.cleaned_data.get("url")
            note.save()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                bookmark_tag, created = \
                    NoteTag.objects.get_or_create(note=note,
                                                      tag=tag)
        return HttpResponseRedirect(reverse('notes:home'))


class EditView(TemplateView):
    def get(self, request, note_id):
        note = Note.objects.get(pk=note_id)
        tags = Tag.objects.filter(notetag__note=note).values_list('name', flat=True)
        data = {}
        data['tags'] = ", ".join(tags)
        data['title'] = note.title
        data['description'] = note.description
        data['url'] = note.url
        data['status'] = note.status
        form = NoteForm(initial=data)
        return render(request,
                      'notes/form.html',
                      {'form': form})

    def post(self, request, note_id):
        note = Note.objects.get(pk=note_id)
        form = NoteForm(request.POST)
        if form.is_valid():
            NoteTag.objects.filter(note=note).delete()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                note_tag, created = NoteTag.objects.get_or_create(note=note, tag=tag)
            note.title = form.cleaned_data.get("title")
            note.url = form.cleaned_data.get("url")
            note.description = form.cleaned_data.get("description")
            note.status = form.cleaned_data.get("status")
            note.save()
        return HttpResponseRedirect(reverse('notes:home'))


class TagView(TemplateView):
    def get(self, request, tag_slug):
        slug_list = tag_slug.split('+')
        tags = Tag.objects.filter(slug__in=slug_list)
        notes = Note.objects.filter(notetag__tag__slug__in=slug_list) \
                .annotate(count=Count('id')) \
                .filter(count=len(slug_list))
        return render(request,
                      'notes/tag.html',
                      {'tags': tags,
                       'notes': notes})


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

        return render(request, 'notes/search.html', {
            'form': form,
            'query': search_query,
            'page': results,
            'total_results': paginator.count,
        })


class FavouritesView(TemplateView):
    def get(self, request):
        tags = Tag.objects.filter(favourite=True)

        return render(request,
                      'notes/fav.html',
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
                      'notes/tags.html',
                      {'page': results})
