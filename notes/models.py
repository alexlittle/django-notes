from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from notes.fields import AutoSlugField

from tinymce.models import HTMLField

STATUS_OPTIONS = (
        ('open', 'Open'),
        ('inprogress', 'In progress'),
        ('closed', 'Closed'),
        ('archived', 'Archived')
    )

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

    class Meta:
        ordering = ['-create_date']

    def __str__(self):
        if self.title:
            return self.title
        else:
            return self.url


class NoteTag(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag,  on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Note Tag')
        verbose_name_plural = _('Note Tags')
