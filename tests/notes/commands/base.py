"""
Shared fixtures/helpers for the `notes` app's management-command tests.

Only the nine command files were provided (not settings/urls/other apps),
so a few things are worth knowing up front - each command's test module
calls out anything relevant inline, and it's all summarised again in
README.md:

- `build_tag_suggestions` needs mlxtend/pandas at runtime (already a
  project dependency, since the command itself imports them).
- `link_checker` hits the network via urllib and prompts on stdin for
  every failed link - both are mocked in its tests rather than exercised
  for real.
- `old_notes` also prompts on stdin per note, and builds an admin URL via
  reverse("admin:notes_note_change", ...) - this assumes Note is
  registered in your admin.py and the admin is wired into your project's
  urls.py, which the command already requires to run at all.
- `import_html` currently crashes on essentially any real bookmarks file -
  see README and that command's test module for details.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from notes.models import Note, NoteTag, Tag

User = get_user_model()

TODAY = date.today()


class NotesCommandTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alex", password="pw12345!")
        self.other_user = User.objects.create_user(username="jamie", password="pw12345!")

    def make_tag(self, user=None, name="tag1", **kwargs):
        return Tag.objects.create(user=user or self.user, name=name, **kwargs)

    def make_note(self, user=None, type="task", title="A note", **kwargs):  # noqa: A002
        return Note.objects.create(user=user or self.user, type=type, title=title, **kwargs)

    def make_bookmark(self, tags=(), **kwargs):
        note = self.make_note(type="bookmark", **kwargs)
        for tag in tags:
            self.tag_note(note, tag)
        return note

    def tag_note(self, note, tag):
        NoteTag.objects.get_or_create(note=note, tag=tag)
