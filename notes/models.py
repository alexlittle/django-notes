import datetime
import pytz

from collections import defaultdict

from django.contrib.auth.models import User
from django.db import models, connection
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.forms.models import model_to_dict

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from notes.fields import AutoSlugField
from notes.utils import get_filtered_notes

from tinymce.models import HTMLField

TIMEZONES = tuple(zip(pytz.all_timezones, pytz.all_timezones))

TYPE_OPTIONS = (
        ('bookmark', 'Bookmark'),
        ('task', 'Task'),
        ('idea', 'Idea'),
    )

FILTER_TYPE_OPTIONS = (
        ('tags', 'Tags'),
        ('search', 'Search')
    )


STATUS_OPTIONS = (
        ('open', 'Open'),
        ('inprogress', 'In progress'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
        ('archived', 'Archived')
    )

PRIORITY_OPTIONS = (
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    )

HISTORY_OPTIONS = (
        ('deferred', 'Deferred'),
        ('updated', 'Updated'),
        ('promoted', 'Promoted')
    )

RECURRENCE_OPTIONS = [
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('biweekly', 'Fortnightly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('annually', 'Annually'),
]

ORDER_BY_OPTIONS =[
    ('-create_date', '-Create Date'),
    ('create_date', 'Create Date'),
    ('-due_date', '-Due Date'),
    ('due_date', 'Due Date'),
    ('-update_date', '-Update Date'),
    ('update_date', 'Update Date'),
    ('title', 'A-Z'),
    ('-title', 'Z-A'),
]

class NotesProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    timezone = models.CharField(max_length=100, blank=True, null=True, choices=TIMEZONES, default='UTC')


class CombinedSearchManager(models.Manager):
    def combined_search(self, user_id, query):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                   DISTINCT note.id
                FROM
                    notes_note note
                INNER JOIN notes_notetag nt ON note.id = nt.note_id
                INNER JOIN notes_tag t ON t.id = nt.tag_id
                WHERE
                    note.user_id = %s
                AND
                    (MATCH(note.type, note.title, note.url, note.description, note.status, note.priority) AGAINST(%s IN NATURAL LANGUAGE MODE)
                OR
                    MATCH (t.name, t.slug) AGAINST (%s IN NATURAL LANGUAGE MODE))

                ;
            """, [user_id, query, query])

            results = [{'id': row[0]} for row in cursor.fetchall()]
        return results


class Tag (models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False, null=False)
    slug = AutoSlugField(populate_from='name',
                         max_length=100,
                         blank=True,
                         null=True,
                         editable=True)
    favourite = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def note_count(self):
        return Note.objects.filter(tags=self).exclude(status__in=['completed', 'archived', 'closed']).count()

    @staticmethod
    def get_top_10_recent_tags():
        """
        Retrieves the 10 most recently used tags, ordered by the latest note creation date.
        """
        recent_tags = Tag.objects.filter(notetag__note__isnull=False).annotate(
            last_used=Note.objects.filter(notetag__tag=models.OuterRef('pk')).order_by('-update_date').values('update_date')[:1]
        ).order_by('-last_used').distinct()[:10]

        return recent_tags


class Note (models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    update_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=15, choices=TYPE_OPTIONS, default='bookmark')
    url = models.TextField(blank=True, null=True)
    title = models.TextField(blank=False, null=False, default=None)
    description = HTMLField(blank=True, null=True)
    link_check_date = models.DateTimeField(default=timezone.now)
    link_check_result = models.TextField(blank=True, null=True)
    favourite = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, through='NoteTag', name='tags')
    status = models.CharField(max_length=15, choices=STATUS_OPTIONS, default='open')
    assistant_loaded = models.BooleanField(default=False)
    due_date = models.DateField(blank=True, null=True, default=None)
    completed_date = models.DateField(blank=True, null=True, default=None)
    estimated_effort = models.IntegerField(blank=True, null=True, default=None)
    priority = models.CharField(max_length=15, choices=PRIORITY_OPTIONS, blank=True, null=True, default=None)
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_OPTIONS, blank=True, null=True, default=None)
    reminder_days = models.IntegerField(default=None, blank=True, null=True)

    class Meta:
        ordering = ['-create_date']

    def __str__(self):
        if self.title:
            return self.title
        else:
            return self.url

    @staticmethod
    def fetch_bookmark_tags():
        notes = defaultdict(list)
        for note in Note.objects.filter(type="bookmark").prefetch_related("tags"):
            notes[note.id] = [tag.slug for tag in note.tags.all()]
        return dict(notes)

    def get_next_due_date(self):
        """Calculate the next due date based on recurrence."""
        if self.recurrence == 'none' or self.recurrence == '' or self.recurrence is None:
            return None
        elif self.recurrence == 'daily':
            return self.due_date + timedelta(days=1)
        elif self.recurrence == 'weekly':
            return self.due_date + timedelta(weeks=1)
        elif self.recurrence == 'biweekly':
            return self.due_date + timedelta(weeks=2)
        elif self.recurrence == 'monthly':
            return self.due_date + relativedelta(months=1)
        elif self.recurrence == 'quarterly':
            return self.due_date + relativedelta(months=3)
        elif self.recurrence == 'annually':
            return self.due_date + relativedelta(years=1)
        return self.due_date

    def generate_next_task(self):
        """Create a new task instance after completion."""
        if self.recurrence == 'none' or self.recurrence == '' or self.recurrence is None:
            return None
        next_due_date = self.get_next_due_date()
        note_data = model_to_dict(self)
        note_data.pop('id', None)
        note_data.pop('tags', None)
        note_data.pop('status', None)
        note_data.pop('create_date', None)
        note_data.pop('completed_date', None)
        note_data['due_date'] = next_due_date
        note_data['user'] = self.user
        new_task = Note.objects.create(**note_data)
        new_task.tags.set(self.tags.all())
        return new_task

    def complete_task(self):
        """Mark the task as completed and create the next one if needed."""
        self.status = 'completed'
        self.completed_date = datetime.datetime.now()
        self.update_date = datetime.datetime.now()
        self.save()
        next_task = self.generate_next_task()

        return next_task

    def uncomplete_task(self):
        """Mark the task as not completed"""
        self.status = 'open'
        self.completed_date = None
        self.update_date = datetime.datetime.now()
        self.save()
        return

    def close_task(self):
        """Mark the task as not completed"""
        self.status = 'closed'
        self.completed_date = None
        self.update_date = datetime.datetime.now()
        self.save()
        return


class NoteHistory (models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    update_date = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=15, choices=HISTORY_OPTIONS, default=None)


class NoteTag(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Note Tag')
        verbose_name_plural = _('Note Tags')


class SavedFilter(models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=15, choices=FILTER_TYPE_OPTIONS, default='tags')
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    order_by = models.CharField(max_length=15, choices=ORDER_BY_OPTIONS, default='due_date')

    class Meta:
        verbose_name = _('Saved Filter')
        verbose_name_plural = _('Saved Filters')
        ordering = ['name']

    def get_count(self, user):
        return get_filtered_notes(user, self.value).count()


class CombinedSearch(models.Model):
    objects = CombinedSearchManager()


class TagSuggestion(models.Model):
    suggested_tag = models.CharField(max_length=100)
    confidence = models.FloatField()
    lift = models.FloatField()
    support = models.FloatField()

    def __str__(self):
        return f"→ {self.suggested_tag}"


class TagSuggestionInputTag(models.Model):
    suggestion = models.ForeignKey(
        TagSuggestion, related_name="input_tags", on_delete=models.CASCADE
    )
    tag = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.tag}"
