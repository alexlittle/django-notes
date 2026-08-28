from datetime import timedelta

from django.urls import reverse

from notes.models import Note, NoteHistory, NoteTag
from tests.base import TODAY, NotesTestCase


class EditViewGetTests(NotesTestCase):
    def test_prefills_form_with_existing_note_data_and_tags(self):
        note = self.make_note(
            type="bookmark", title="Existing", url="https://example.com", status="open"
        )
        tag_a = self.make_tag(name="alpha")
        tag_b = self.make_tag(name="beta")
        self.tag_note(note, tag_a)
        self.tag_note(note, tag_b)

        resp = self.client.get(reverse("notes:edit", kwargs={"note_id": note.pk}))

        initial = resp.context["form"].initial
        self.assertEqual(initial["title"], "Existing")
        self.assertEqual(initial["url"], "https://example.com")
        self.assertCountEqual(initial["tags"].split(", "), ["alpha", "beta"])

    def test_cannot_load_another_users_note(self):
        note = self.make_note(user=self.other_user, title="Not mine")

        with self.assertRaises(Note.DoesNotExist):
            self.client.get(reverse("notes:edit", kwargs={"note_id": note.pk}))


class EditViewPostTests(NotesTestCase):
    def _post(self, note, **overrides):
        data = {
            "type": note.type,
            "title": note.title,
            "tags": "updated-tag",
            "status": note.status,
            "priority": note.priority or "medium",
            "url": note.url or "",
        }
        # Preserve due_date/recurrence unless a test deliberately overrides
        # them - both fields are optional, so omitting either from the POST
        # body would otherwise silently clear it on every save (which is
        # exactly what the view does: it always writes cleaned_data, even
        # when that's empty because the field wasn't submitted).
        if note.due_date:
            data["due_date"] = note.due_date.isoformat()
        if note.recurrence:
            data["recurrence"] = note.recurrence
        data.update(overrides)
        return self.client.post(reverse("notes:edit", kwargs={"note_id": note.pk}), data)

    def test_updates_fields_and_replaces_tags(self):
        note = self.make_task(title="Old title")
        old_tag = self.make_tag(name="old-tag")
        self.tag_note(note, old_tag)

        self._post(note, title="New title", tags="new-tag")

        note.refresh_from_db()
        self.assertEqual(note.title, "New title")
        remaining_tags = sorted(nt.tag.name for nt in NoteTag.objects.filter(note=note))
        self.assertEqual(remaining_tags, ["new-tag"])

    def test_due_date_moved_later_is_recorded_as_deferred(self):
        note = self.make_task(title="Task", due_date=TODAY)

        self._post(note, due_date=(TODAY + timedelta(days=5)).isoformat())

        history = NoteHistory.objects.filter(note=note).latest("update_date")
        self.assertEqual(history.action, "deferred")

    def test_due_date_moved_earlier_is_recorded_as_promoted(self):
        note = self.make_task(title="Task", due_date=TODAY + timedelta(days=5))

        self._post(note, due_date=TODAY.isoformat())

        history = NoteHistory.objects.filter(note=note).latest("update_date")
        self.assertEqual(history.action, "promoted")

    def test_no_prior_due_date_is_recorded_as_updated(self):
        note = self.make_task(title="Task", due_date=None)

        self._post(note, due_date=(TODAY + timedelta(days=5)).isoformat())

        history = NoteHistory.objects.filter(note=note).latest("update_date")
        self.assertEqual(history.action, "updated")

    def test_marking_a_non_recurring_task_completed_sets_status_and_completed_date(self):
        note = self.make_task(title="Task", due_date=TODAY, status="open", recurrence="")

        self._post(note, status="completed")

        note.refresh_from_db()
        self.assertEqual(note.status, "completed")
        self.assertIsNotNone(note.completed_date)
        self.assertEqual(Note.objects.filter(title="Task").count(), 1)

    def test_marking_a_recurring_task_completed_archives_it_and_spawns_the_next_one(self):
        note = self.make_task(
            title="Recurring task", due_date=TODAY, status="open", recurrence="weekly"
        )

        self._post(note, status="completed")

        note.refresh_from_db()
        self.assertEqual(note.status, "archived")
        next_task = Note.objects.exclude(pk=note.pk).get(title="Recurring task")
        self.assertEqual(next_task.due_date, TODAY + timedelta(weeks=1))
        self.assertEqual(next_task.status, "open")

    def test_re_saving_an_already_completed_task_does_not_retrigger_completion(self):
        note = self.make_task(
            title="Already done", due_date=TODAY, status="completed", recurrence="weekly"
        )

        self._post(note, status="completed")

        # old_status was already "completed", so the "just completed" branch
        # never fires and no extra recurring task should be spawned.
        self.assertEqual(Note.objects.filter(title="Already done").count(), 1)

    def test_invalid_post_re_renders_form_without_saving(self):
        note = self.make_task(title="Task", due_date=TODAY, priority="high")

        resp = self._post(note, priority="")

        self.assertEqual(resp.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.title, "Task")  # unchanged

    def test_redirects_to_referer_when_present(self):
        # Unlike the Complete/UnComplete/Close views, EditView.post() reads
        # `referer` from the *submitted form field* (form.cleaned_data),
        # not the HTTP_REFERER header - it only gets that value because
        # EditView.get() pre-fills it as a hidden field from the header on
        # page load. So the test has to post the field, not set the header.
        note = self.make_task(title="Task", due_date=TODAY)

        resp = self.client.post(
            reverse("notes:edit", kwargs={"note_id": note.pk}),
            {
                "type": "task",
                "title": "Task",
                "tags": "x",
                "status": "open",
                "priority": "medium",
                "referer": "/notes/tasks/",
            },
        )

        self.assertRedirects(resp, "/notes/tasks/", fetch_redirect_response=False)
