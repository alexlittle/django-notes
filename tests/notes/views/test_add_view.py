from django.urls import reverse

from notes.models import Note, NoteTag
from tests.base import NotesTestCase


class AddViewGetTests(NotesTestCase):
    def test_birthday_shortcut_prefills_recurring_annual_task(self):
        resp = self.client.get(reverse("notes:add"), {"type": "birthday"})

        initial = resp.context["form"].initial
        self.assertEqual(initial["type"], "task")
        self.assertEqual(initial["tags"], "birthdays")
        self.assertEqual(initial["recurrence"], "annually")
        self.assertEqual(initial["reminder_days"], 14)

    def test_task_shortcut_prefills_today_and_medium_priority(self):
        resp = self.client.get(reverse("notes:add"), {"type": "task"})

        initial = resp.context["form"].initial
        self.assertEqual(initial["type"], "task")
        self.assertEqual(initial["priority"], "medium")
        self.assertIn("due_date", initial)

    def test_tags_query_param_overrides_default_tags(self):
        resp = self.client.get(reverse("notes:add"), {"type": "birthday", "tags": "custom,tags"})

        self.assertEqual(resp.context["form"].initial["tags"], "custom,tags")

    def test_referer_is_carried_into_the_form(self):
        resp = self.client.get(reverse("notes:add"), HTTP_REFERER="/notes/tasks/")

        self.assertEqual(resp.context["form"].initial["referer"], "/notes/tasks/")


class AddViewPostTests(NotesTestCase):
    def _valid_task_data(self, **overrides):
        data = {
            "type": "task",
            "title": "New task",
            "tags": "work, urgent",
            "status": "open",
            "priority": "high",
        }
        data.update(overrides)
        return data

    def test_valid_post_creates_a_note_and_its_tags(self):
        resp = self.client.post(reverse("notes:add"), self._valid_task_data())

        note = Note.objects.get(title="New task")
        self.assertEqual(note.user, self.user)
        self.assertEqual(note.type, "task")
        tag_names = sorted(nt.tag.name for nt in NoteTag.objects.filter(note=note))
        self.assertEqual(tag_names, ["urgent", "work"])
        self.assertRedirects(resp, reverse("notes:home"), fetch_redirect_response=False)

    def test_task_without_priority_is_rejected(self):
        resp = self.client.post(reverse("notes:add"), self._valid_task_data(priority=""))

        self.assertEqual(resp.status_code, 200)  # re-rendered form, not redirected
        self.assertFalse(Note.objects.filter(title="New task").exists())
        self.assertIn("A task must have a priority", resp.context["form"].errors["__all__"])

    def test_bookmark_without_url_is_rejected(self):
        data = {
            "type": "bookmark",
            "title": "New bookmark",
            "tags": "reading",
            "status": "open",
        }
        resp = self.client.post(reverse("notes:add"), data)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Note.objects.filter(title="New bookmark").exists())
        self.assertIn("A bookmark must have a url", resp.context["form"].errors["__all__"])

    def test_save_and_add_redirects_back_to_add_with_type(self):
        resp = self.client.post(reverse("notes:add"), self._valid_task_data(action="save_and_add"))

        self.assertRedirects(
            resp, reverse("notes:add") + "?type=task", fetch_redirect_response=False
        )

    def test_save_redirects_to_referer_when_present(self):
        data = self._valid_task_data(referer="/notes/tasks/")
        resp = self.client.post(reverse("notes:add"), data)

        self.assertRedirects(resp, "/notes/tasks/", fetch_redirect_response=False)

    def test_empty_entries_in_the_tags_list_are_ignored(self):
        self.client.post(reverse("notes:add"), self._valid_task_data(tags="work,, urgent,"))

        note = Note.objects.get(title="New task")
        tag_names = sorted(nt.tag.name for nt in NoteTag.objects.filter(note=note))
        self.assertEqual(tag_names, ["urgent", "work"])
