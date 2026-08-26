from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse

from notes.models import Tag
from tests.base import TODAY, NotesTestCase


class TasksViewTests(NotesTestCase):
    def _get(self, showall=False):
        with patch("notes.views.is_showall", return_value=showall):
            return self.client.get(reverse("notes:tasks"))

    def test_only_shows_tasks_for_current_user(self):
        mine = self.make_task(title="Mine")
        self.make_task(user=self.other_user, title="Not mine")
        self.make_note(type="bookmark", title="Bookmark")

        resp = self._get()

        self.assertEqual(list(resp.context["tasks"]), [mine])

    def test_default_hides_completed_closed_and_archived(self):
        open_task = self.make_task(title="Open", status="open")
        self.make_task(title="Completed", status="completed")
        self.make_task(title="Closed", status="closed")
        self.make_task(title="Archived", status="archived")

        resp = self._get(showall=False)

        self.assertEqual(list(resp.context["tasks"]), [open_task])

    def test_showall_includes_everything(self):
        self.make_task(title="Open", status="open")
        self.make_task(title="Completed", status="completed")

        resp = self._get(showall=True)

        self.assertEqual(len(resp.context["tasks"]), 2)

    def test_dated_tasks_are_ordered_before_undated_tasks(self):
        undated = self.make_task(title="Undated", due_date=None)
        dated = self.make_task(title="Dated", due_date=TODAY + timedelta(days=5))

        resp = self._get(showall=True)

        self.assertEqual(list(resp.context["tasks"]), [dated, undated])

    def test_dated_tasks_ordered_by_due_date_ascending(self):
        later = self.make_task(title="Later", due_date=TODAY + timedelta(days=10))
        sooner = self.make_task(title="Sooner", due_date=TODAY + timedelta(days=1))

        resp = self._get(showall=True)

        self.assertEqual(list(resp.context["tasks"]), [sooner, later])


class TagTasksViewTests(NotesTestCase):
    def setUp(self):
        super().setUp()
        self.tag = self.make_tag(name="work")

    def _url(self):
        return reverse("notes:tag_tasks", kwargs={"tag_slug": self.tag.slug})

    def _get(self, showall=False):
        with patch("notes.views.is_showall", return_value=showall):
            return self.client.get(self._url())

    def test_only_tasks_with_the_given_tag_are_shown(self):
        tagged = self.make_task(title="Tagged")
        self.tag_note(tagged, self.tag)
        untagged = self.make_task(title="Untagged")

        resp = self._get()

        self.assertEqual(list(resp.context["tasks"]), [tagged])
        self.assertNotIn(untagged, resp.context["tasks"])

    def test_only_task_type_notes_are_shown_even_if_tagged(self):
        bookmark = self.make_note(type="bookmark", title="Bookmarked")
        self.tag_note(bookmark, self.tag)

        resp = self._get()

        self.assertEqual(len(resp.context["tasks"]), 0)

    def test_showall_controls_status_filtering(self):
        completed = self.make_task(title="Completed", status="completed")
        self.tag_note(completed, self.tag)

        hidden = self._get(showall=False)
        self.assertNotIn(completed, hidden.context["tasks"])

        shown = self._get(showall=True)
        self.assertIn(completed, shown.context["tasks"])

    def test_context_includes_the_tag_and_showall_flag(self):
        with patch("notes.views.is_showall", return_value=True):
            resp = self.client.get(self._url())

        self.assertEqual(resp.context["tag"], self.tag)
        self.assertTrue(resp.context["showall"])

    def test_unknown_tag_slug_raises_does_not_exist(self):
        # Current behaviour: Tag.objects.get() is called unguarded, so a
        # bad/missing slug bubbles up as a 500 rather than a 404. See README.
        url = reverse("notes:tag_tasks", kwargs={"tag_slug": "does-not-exist"})
        with (
            patch("notes.views.is_showall", return_value=False),
            self.assertRaises(Tag.DoesNotExist),
        ):
            self.client.get(url)
