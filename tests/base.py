"""
Shared fixtures and helpers for `notes` app view tests.

See README.md in this folder for the assumptions these tests make about
things that weren't in the four uploaded files (utils functions, templates,
the MySQL-only search query, etc).
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from notes.models import Note, NoteTag, Tag

User = get_user_model()

# Computed once at import time and reused everywhere, so every test agrees
# on what "today" is - including the bits of HomeView that call
# datetime.now() directly rather than going through get_user_aware_date.
TODAY = date.today()


class NotesTestCase(TestCase):
    """Base class: a logged-in user plus a second user for isolation checks."""

    def setUp(self):
        self.user = User.objects.create_user(username="alex", password="pw12345!")
        self.other_user = User.objects.create_user(username="jamie", password="pw12345!")
        self.client.force_login(self.user)

    def make_tag(self, user=None, name="tag1", **kwargs):
        return Tag.objects.create(user=user or self.user, name=name, **kwargs)

    def make_note(self, user=None, type="task", title="A note", **kwargs):  # noqa: A002
        return Note.objects.create(user=user or self.user, type=type, title=title, **kwargs)

    def make_task(self, **kwargs):
        kwargs.setdefault("status", "open")
        return self.make_note(type="task", **kwargs)

    def tag_note(self, note, tag):
        NoteTag.objects.get_or_create(note=note, tag=tag)
