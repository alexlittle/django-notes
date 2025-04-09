
from django.urls import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models import Count, Case, When, Value, DateField, IntegerField
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from datetime import datetime
from datetime import timedelta

from notes.forms import NoteForm, SearchForm
from notes.models import Note, Tag, NoteTag, NoteHistory, CombinedSearch
from notes.utils import get_user_aware_date, is_showall

class HomeView(TemplateView):
    template_name = 'notes/home.html'

    def _filter_for_reminders(self, base_query):
        reminder_items = []
        for item in base_query.filter(reminder_days__gt=0):
            due_threshold = item.due_date - timedelta(days=item.reminder_days)

            if datetime.now().date() >= due_threshold and item.due_date != datetime.now().date():
                reminder_items.append(item)
        return reminder_items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_aware_now = get_user_aware_date(self.request.user)
        showall = is_showall(self.request)

        base_query_dated = Note.objects.filter(user=self.request.user,
                                               due_date__isnull=False,
                                               type="task",
                                               status__in=['open', 'inprogress', 'completed']) \
                                        .annotate(
                                            priority_order=Case(
                                                When(priority='high', then=Value(1)),
                                                When(priority='medium', then=Value(2)),
                                                When(priority='low', then=Value(3)),
                                                default=Value(4),
                                                output_field=IntegerField()
                                            )
                                        ) \
                                        .annotate(
                                            status_order=Case(
                                                When(status='completed', then=Value(0)),
                                                default=Value(1),
                                                output_field=IntegerField()
                                            )
                                        )
        if not showall:
            base_query_dated = base_query_dated.exclude(status='completed')

        context["overdue"] = base_query_dated.exclude(status='completed').filter(due_date__lt=user_aware_now).order_by("priority_order", "due_date")
        context["reminder"] = self._filter_for_reminders(base_query_dated.exclude(status='completed').order_by("due_date"))
        queryset = base_query_dated.filter(due_date=user_aware_now).order_by("-status_order", "priority_order")
        context["today"] = queryset
        context["tomorrow"] = base_query_dated.filter(due_date=user_aware_now+timedelta(days=1)).order_by("-status_order", "priority_order")
        context["next_week"] = base_query_dated.filter(due_date__gt=user_aware_now+timedelta(days=1),
                                                       due_date__lte=user_aware_now+timedelta(days=7)).order_by("due_date", "priority_order")
        context["next_month"] = base_query_dated.filter(due_date__gt=user_aware_now + timedelta(days=7),
                                                       due_date__lte=user_aware_now + timedelta(days=31)).order_by("due_date", "priority_order")
        context["showall"] = showall
        return context


class FutureTasksView(TemplateView):
    template_name = 'notes/tasks_future.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_aware_now = get_user_aware_date(self.request.user)
        base_query_dated = Note.objects.filter(user=self.request.user,
                                               due_date__isnull=False,
                                               type="task",
                                               status__in=['open', 'inprogress', 'completed'])

        showall = is_showall(self.request)
        if not showall:
            base_query_dated = base_query_dated.exclude(status='completed')
        context["future"] = base_query_dated.filter(due_date__gt=user_aware_now+timedelta(days=31)).order_by("due_date")

        showall = is_showall(self.request)
        context["showall"] = showall

        return context


class TasksView(ListView):
    template_name = 'notes/tasks.html'
    paginate_by = 50
    context_object_name = 'tasks'

    def get_queryset(self):
        showall = is_showall(self.request)
        qs = Note.objects.filter(user=self.request.user, type="task").annotate(
            has_date=Case(
                When(due_date__isnull=False, then=Value(1)),
                default=Value(0),
                output_field=DateField(),
            )
        )
        if not showall:
            qs = qs.filter(status__in=['open', 'inprogress'])

        return qs.order_by('-has_date', 'due_date')

class TasksTagsView(TemplateView):
    template_name = 'notes/tasks_tags.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        showall = is_showall(self.request)
        context["showall"] = showall

        base_query_dated = Note.objects.filter(user=self.request.user, due_date__isnull=False, type="task")
        base_query_undated = Note.objects.filter(user=self.request.user, due_date__isnull=True, type="task")
        if not showall:
            base_query_dated = base_query_dated.filter(status__in=['open', 'inprogress'])
            base_query_undated = base_query_undated.filter(status__in=['open', 'inprogress'])

        context["tags_dated"] = Tag.objects.filter(user=self.request.user, notetag__note__in=base_query_dated) \
            .distinct() \
            .annotate(note_count=Count("notetag__note")) \
            .order_by("name")
        context["tags_undated"] = Tag.objects.filter(user=self.request.user, notetag__note__in=base_query_undated) \
            .distinct() \
            .annotate(note_count=Count("notetag__note")) \
            .order_by("name")
        return context


class TagTasksView(ListView):
    template_name = 'notes/tasks.html'
    paginate_by = 50
    context_object_name = 'tasks'

    def get_queryset(self):
        slug = self.kwargs['tag_slug']
        showall = is_showall(self.request)
        notes = Note.objects.filter(user=self.request.user, notetag__tag__slug=slug, type="task")
        if not showall:
            notes = notes.filter(status__in=['open', 'inprogress'])
        return notes.annotate(
                    has_date=Case(
                        When(due_date__isnull=False, then=Value(1)),
                        default=Value(0),
                        output_field=DateField(),
                    )
                ).order_by('-has_date', 'due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['tag_slug']
        context["tag"] = Tag.objects.get(user=self.request.user, slug=slug)

        showall = is_showall(self.request)
        context["showall"] = showall

        return context


class BookmarksView(ListView):
    template_name = 'notes/bookmarks.html'
    paginate_by = 50
    context_object_name = 'notes'

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user, type="bookmark").order_by('-create_date')

class IdeasView(ListView):
    template_name = 'notes/ideas.html'
    paginate_by = 50
    context_object_name = 'notes'

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user, type="idea").order_by('-create_date')

class CompleteTaskView(TemplateView):

    def get(self, request, note_id):
        note = Note.objects.get(user=self.request.user, pk=note_id)
        note.complete_task()
        referer = request.META.get('HTTP_REFERER')

        if referer:
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('notes:home'))

class UnCompleteTaskView(TemplateView):

    def get(self, request, note_id):
        note = Note.objects.get(user=self.request.user, pk=note_id)
        note.uncomplete_task()
        referer = request.META.get('HTTP_REFERER')

        if referer:
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('notes:home'))

class CloseTaskView(TemplateView):

    def get(self, request, note_id):
        note = Note.objects.get(user=self.request.user, pk=note_id)
        note.close_task()
        referer = request.META.get('HTTP_REFERER')

        if referer:
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('notes:home'))


class AddView(TemplateView):

    def get(self, request):
        form_type = request.GET.get('type')
        initial_data = {'referer': request.META.get('HTTP_REFERER')}
        recent_tags = Tag.get_top_10_recent_tags()
        if form_type == 'birthday':
            initial_data['type'] = 'task'
            initial_data['tags'] = 'birthdays'
            initial_data['recurrence'] = 'annually'
            initial_data['reminder_days'] = 14
        elif form_type == 'task':
            initial_data['type'] = 'task'
            initial_data['estimated_effort'] = 15
            initial_data['due_date'] = datetime.now().date()
            initial_data['priority'] = "medium"
        elif form_type == 'idea':
            initial_data['type'] = 'idea'
        elif form_type == 'bookmark':
            initial_data['type'] = 'bookmark'
        if request.GET.get('tags'):
            initial_data['tags'] = request.GET.get('tags')
        form = NoteForm(initial=initial_data)
        return render(request,
                      'notes/form.html',
                      {'form': form, 'recent_tags': recent_tags})

    def post(self, request):
        form = NoteForm(request.POST)
        form_type = request.POST.get('type')
        if form.is_valid():
            note = Note()
            note.user = request.user
            note.type = form.cleaned_data.get("type")
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
            tags = [tag for tag in tags if tag]
            for t in tags:
                tag, created = Tag.objects.get_or_create(user=self.request.user, name=t)
                NoteTag.objects.get_or_create(note=note, tag=tag)

            if request.POST.get("action") == "save_and_add":
                redirect_url = reverse('notes:add')
                if form_type:
                    redirect_url += f'?type={form_type}'
                return HttpResponseRedirect(redirect_url)
            else:
                referer = form.cleaned_data.get("referer")
                if referer:
                    return HttpResponseRedirect(referer)
                else:
                    return HttpResponseRedirect(reverse('notes:home'))
        else:
            print(form.errors)
            context = {'form': form, 'form_type': form_type}
            return render(request, 'notes/form.html', context)

class EditView(TemplateView):

    def get(self, request, note_id):
        note = Note.objects.get(user=self.request.user, pk=note_id)
        tags = Tag.objects.filter(user=self.request.user, notetag__note=note).values_list('name', flat=True)
        data = {}
        data['tags'] = ", ".join(tags)
        data['type'] = note.type
        data['title'] = note.title
        data['description'] = note.description
        data['url'] = note.url
        data['status'] = note.status
        data['due_date'] = note.due_date
        data['estimated_effort'] = note.estimated_effort
        data['priority'] = note.priority
        data['recurrence'] = note.recurrence
        data['reminder_days'] = note.reminder_days
        recent_tags = Tag.get_top_10_recent_tags()
        form = NoteForm(initial=data)
        return render(request,
                      'notes/form.html',
                      {'form': form, 'recent_tags': recent_tags})

    def post(self, request, note_id):
        note = Note.objects.get(user=self.request.user, pk=note_id)
        form = NoteForm(request.POST)
        if form.is_valid():
            NoteTag.objects.filter(note=note).delete()
            new_tags = form.cleaned_data.get("tags")
            tags = [x.strip() for x in new_tags.split(',')]
            tags = [tag for tag in tags if tag]
            for t in tags:
                tag, created = Tag.objects.get_or_create(user=self.request.user, name=t)
                NoteTag.objects.get_or_create(note=note, tag=tag)

            old_status = note.status
            old_due_date = note.due_date
            note.user = request.user
            note.type = form.cleaned_data.get("type")
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
            if old_due_date:
                if old_due_date <= note.due_date:
                    nh.action = "deferred"
                else:
                    nh.action = "promoted"
            else:
                nh.action = "updated"
            nh.save()
        return HttpResponseRedirect(reverse('notes:home'))


class TagView(ListView):
    template_name = 'notes/tag.html'
    context_object_name = 'notes'

    def get_queryset(self):
        slug_list = self.kwargs['tag_slug'].split('+')
        return Note.objects.filter(user=self.request.user, notetag__tag__slug__in=slug_list) \
                .annotate(count=Count('id')) \
                .filter(count=len(slug_list))

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        slug_list = self.kwargs['tag_slug'].split('+')
        context["tags"] = Tag.objects.filter(user=self.request.user, slug__in=slug_list)
        return context


class SearchView(ListView):
    template_name = 'notes/search.html'
    context_object_name = 'notes'
    paginate_by = 50

    def get_queryset(self):
        search_query = self.request.GET.get('q', '')

        if search_query:
            search_id_results = CombinedSearch.objects.combined_search(self.request.user.id, search_query)
            search_ids = [result['id'] for result in search_id_results]
        else:
            search_ids = []

        return Note.objects.filter(pk__in=search_ids)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('q', '')
        data = {'q': search_query}
        form = SearchForm(initial=data)

        context['form'] = form
        context['query'] = search_query
        context['total_results'] = self.get_queryset().count() #add total count of results.
        return context


class FavouritesView(ListView):

    template_name = 'notes/fav.html'
    context_object_name = 'tags'

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user, favourite=True)


class TagsView(ListView):

    template_name = 'notes/tags.html'
    paginate_by = 50
    context_object_name = 'tags'

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user).order_by('-favourite', 'name')
