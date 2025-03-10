from django.conf import settings
from django.urls import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from notes.forms import NoteForm, SearchForm
from notes.models import Note, Tag, NoteTag, NoteHistory
from haystack.query import SearchQuerySet

#from assistant.airag import NotesAssistant

class HomeView(ListView):
    template_name = 'notes/home.html'
    paginate_by = 50
    context_object_name = 'tasks'

    def get_queryset(self):
        return Note.objects.filter(due_date__isnull=False, status__in=['open', 'inprogress']).order_by('due_date')


class NotesView(ListView):
    template_name = 'notes/notes.html'
    paginate_by = 50
    context_object_name = 'notes'

    def get_queryset(self):
        return Note.objects.all().order_by('-create_date')


class CompleteTaskView(TemplateView):

    def get(self, request, note_id):
        note = Note.objects.get(pk=note_id)
        note.complete_task()
        return HttpResponseRedirect(reverse('notes:home'))


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
            note.due_date = form.cleaned_data.get("due_date")
            note.estimated_effort = form.cleaned_data.get("estimated_effort")
            note.priority = form.cleaned_data.get("priority")
            note.recurrence = form.cleaned_data.get("recurrence")
            note.reminder_days = form.cleaned_data.get("reminder_days")
            note.save()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            for t in tags:
                tag, created = Tag.objects.get_or_create(name=t)
                NoteTag.objects.get_or_create(note=note, tag=tag)
            if settings.NOTES_ASSISTANT_ENABLED and note.url is not None:
                #assistant = NotesAssistant()
                #assistant.add_note(note.url)
                pass
            if request.POST.get("action") == "save_and_add":
                return HttpResponseRedirect(reverse('notes:add'))
            else:
                return HttpResponseRedirect(reverse('notes:home'))
        else:
            print(form.errors)

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
        data['due_date'] = note.due_date
        data['estimated_effort'] = note.estimated_effort
        data['priority'] = note.priority
        data['recurrence'] = note.recurrence
        data['reminder_days'] = note.reminder_days
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

            old_status = note.status
            old_due_date = note.due_date
            note.title = form.cleaned_data.get("title")
            note.url = form.cleaned_data.get("url")
            note.description = form.cleaned_data.get("description")
            note.status = form.cleaned_data.get("status")
            note.due_date = form.cleaned_data.get("due_date")
            note.estimated_effort = form.cleaned_data.get("estimated_effort")
            note.priority = form.cleaned_data.get("priority")
            note.recurrence = form.cleaned_data.get("recurrence")
            note.reminder_days = form.cleaned_data.get("reminder_days")
            # if completed check if recurring
            completed_status_key = 'completed'
            if old_status != completed_status_key and form.cleaned_data.get("status") == completed_status_key:
                note.complete_task()
            note.save()

            nh = NoteHistory()
            nh.note = note
            if old_due_date != note.due_date:
                nh.action = "deferred"
            else:
                nh.action = "updated"
            nh.save()
        return HttpResponseRedirect(reverse('notes:home'))


class TagView(ListView):
    template_name = 'notes/tag.html'
    context_object_name = 'notes'

    def get_queryset(self):
        slug_list = self.kwargs['tag_slug'].split('+')
        return Note.objects.filter(notetag__tag__slug__in=slug_list) \
                .annotate(count=Count('id')) \
                .filter(count=len(slug_list))

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        slug_list = self.kwargs['tag_slug'].split('+')
        context["tags"] = Tag.objects.filter(slug__in=slug_list)
        return context


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


class FavouritesView(ListView):

    template_name = 'notes/fav.html'
    context_object_name = 'tags'

    def get_queryset(self):
        return Tag.objects.filter(favourite=True)


class TagsView(ListView):

    template_name = 'notes/tags.html'
    paginate_by = 50
    context_object_name = 'tags'

    def get_queryset(self):
        return Tag.objects.all().order_by('-favourite', 'name')
