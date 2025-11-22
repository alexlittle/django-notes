
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Case, When, Value, DateField, IntegerField
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from datetime import datetime
from datetime import timedelta

from notes.forms import NoteForm, SearchForm
from notes.models import Note, Tag, NoteTag, NoteHistory, CombinedSearch, SavedFilter, NotesConfig
from notes.utils import get_user_aware_date, is_showall, get_filtered_notes
from notes.libs.association import suggest_tags

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
        queryset = base_query_dated.filter(due_date=user_aware_now).order_by("-status_order", "priority_order", "title")
        context["today"] = queryset
        context["tomorrow"] = base_query_dated.filter(due_date=user_aware_now+timedelta(days=1)).order_by("-status_order", "priority_order", "title")
        context["next_week"] = base_query_dated.filter(due_date__gt=user_aware_now+timedelta(days=1),
                                                       due_date__lte=user_aware_now+timedelta(days=7)).order_by("due_date", "priority_order", "title")
        context["next_month"] = base_query_dated.filter(due_date__gt=user_aware_now + timedelta(days=7),
                                                       due_date__lte=user_aware_now + timedelta(days=31)).order_by("due_date", "priority_order", "title")
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


class RecentView(ListView):
    template_name = 'notes/recent.html'
    paginate_by = 50
    context_object_name = 'tasks'

    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user)
        return qs.order_by('-update_date', 'create_date')[:self.paginate_by]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["showall"] = is_showall(self.request)
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
        context["showall"] = is_showall(self.request)
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
            note.update_date = timezone.now()
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
        data['referer'] = request.META.get('HTTP_REFERER')
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
            note.update_date = timezone.now()
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
            if old_due_date and note.due_date:
                if old_due_date <= note.due_date:
                    nh.action = "deferred"
                else:
                    nh.action = "promoted"
            else:
                nh.action = "updated"
            nh.save()
            referer = form.cleaned_data.get("referer")
            if referer:
                return HttpResponseRedirect(referer)
            else:
                return HttpResponseRedirect(reverse('notes:home'))
        else:
            print(form.errors)
            context = {'form': form}
            return render(request, 'notes/form.html', context)


class TagView(ListView):
    template_name = 'notes/tag.html'
    context_object_name = 'notes'

    def get_queryset(self):
        order_by = self.request.GET.get('order', '-due_date')
        return get_filtered_notes(self.request.user, self.kwargs['tag_slug']).order_by(order_by, '-create_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug_list = self.kwargs['tag_slug'].split('+')
        context["tags"] = Tag.objects.filter(user=self.request.user, slug__in=slug_list)
        context["related_tags"] = suggest_tags(slug_list)

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
        context['total_results'] = self.get_queryset().count()
        return context


class FavouritesView(TemplateView):

    template_name = 'notes/fav.html'
    context_object_name = 'tags'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.filter(user=self.request.user,
                                             favourite=True)
        context['filters'] = [(fn, fn.get_count(self.request.user)) for fn in SavedFilter.objects.all()]
        return context


class TagsView(ListView):

    template_name = 'notes/tags.html'
    paginate_by = 50
    context_object_name = 'tags'

    def get_queryset(self):
        ordering = self.request.GET.get('orderby', '-favourite')
        return Tag.objects.filter(user=self.request.user).annotate(count=Count('notetag__note__id')).order_by(ordering, 'name')


class WeeklyScheduleView(TemplateView):
    template_name = 'notes/weekly-schedule.html'
    study_tag_slug = 'study'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_tags = [tag.strip() for tag in NotesConfig.get_value("schedule.study.tags").split(',')]

        start_days = int(NotesConfig.get_value("schedule.start.days"))
        end_days = int(NotesConfig.get_value("schedule.end.days"))
        start_date = timezone.localdate() - timedelta(days=start_days)
        end_date = timezone.localdate() + timedelta(days=end_days)

        course_tag_objs = Tag.objects.filter(slug__in=course_tags)
        study_tag = Tag.objects.get(name=self.study_tag_slug)
        weeks = []
        current = start_date
        while current <= end_date:
            week_end = current + timedelta(days=(4 - current.weekday()) % 7)  # Friday
            weeks.append({
                'label': week_end.strftime("Fri %d %b"),
                'start': current,
                'end': week_end,
                'is_current': current <= timezone.now().date() <= week_end
            })
            current = week_end + timedelta(days=1)

        context['weeks'] = weeks

        # Prepare grid: rows = course tags, columns = weeks
        grid = {}
        for tag in course_tag_objs:
            grid[tag.id] = []
            for week in weeks:
                tasks = Note.objects.filter(type='task',
                                            due_date__range=(week['start'], week['end']),
                                            status__in=['open', 'inprogress', 'completed']) \
                    .filter(tags__name=study_tag) \
                    .filter(tags__name=tag.name) \
                    .distinct() \
                    .order_by('due_date','title')
                grid[tag.id].append({
                    'week': week,
                    'tasks': tasks
                })

        context['grid'] = grid
        context['course_tags'] = course_tag_objs
        return context

