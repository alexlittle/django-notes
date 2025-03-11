import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.forms.models import model_to_dict

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from notes.fields import AutoSlugField

from tinymce.models import HTMLField

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
        ('updated', 'Updated')
    )

RECURRENCE_OPTIONS = [
    ('weekly', 'Weekly'),
    ('biweekly', 'Fortnightly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('annually', 'Annually'),
]


class Tag (models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100, blank=False, null=False)
    slug = AutoSlugField(populate_from='name',
                         max_length=100,
                         blank=True,
                         null=True)
    favourite = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def note_count(self):
        return Note.objects.filter(tags=self).count()


class Note (models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
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
    estimated_effort = models.IntegerField(default=30)
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

    def get_next_due_date(self):
        """Calculate the next due date based on recurrence."""
        if self.recurrence == 'none' or self.recurrence is None:
            return None
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
        if self.recurrence == 'none' or self.recurrence is None:
            return None
        next_due_date = self.get_next_due_date()
        note_data = model_to_dict(self)
        note_data.pop('id', None)
        note_data.pop('tags', None)
        note_data.pop('status', None)
        note_data.pop('create_date', None)
        note_data.pop('completed_date', None)
        note_data['due_date'] = next_due_date

        new_task = Note.objects.create(**note_data)
        new_task.tags.set(self.tags.all())
        return new_task

    def complete_task(self):
        """Mark the task as completed and create the next one if needed."""
        self.status = 'completed'
        self.completed_date = datetime.datetime.now()
        self.save()
        next_task = self.generate_next_task()

        return next_task


class NoteHistory (models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    update_date = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=15, choices=HISTORY_OPTIONS, default=None)


class NoteTag(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag,  on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Note Tag')
        verbose_name_plural = _('Note Tags')
