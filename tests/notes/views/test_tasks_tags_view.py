from unittest.mock import patch

from django.urls import reverse

from tests.base import NotesTestCase


class TasksTagsViewTests(NotesTestCase):
    def _get(self, showall=False):
        with patch("notes.views.is_showall", return_value=showall):
            return self.client.get(reverse("notes:tasks_tags_home"))

    def test_splits_tags_into_dated_and_undated_buckets(self):
        dated_tag = self.make_tag(name="dated")
        undated_tag = self.make_tag(name="undated")

        dated_task = self.make_task(title="Dated", due_date="2026-09-01")
        self.tag_note(dated_task, dated_tag)

        undated_task = self.make_task(title="Undated", due_date=None)
        self.tag_note(undated_task, undated_tag)

        resp = self._get()

        self.assertIn(dated_tag, resp.context["tags_dated"])
        self.assertNotIn(undated_tag, resp.context["tags_dated"])
        self.assertIn(undated_tag, resp.context["tags_undated"])
        self.assertNotIn(dated_tag, resp.context["tags_undated"])

    def test_tags_on_non_task_notes_are_excluded(self):
        tag = self.make_tag(name="bookmark-tag")
        bookmark = self.make_note(type="bookmark", title="Bookmark", due_date="2026-09-01")
        self.tag_note(bookmark, tag)

        resp = self._get()

        self.assertNotIn(tag, resp.context["tags_dated"])
        self.assertNotIn(tag, resp.context["tags_undated"])

    def test_note_count_annotation(self):
        tag = self.make_tag(name="popular")
        for i in range(3):
            task = self.make_task(title=f"Task {i}", due_date=None)
            self.tag_note(task, tag)

        resp = self._get()

        found = resp.context["tags_undated"].get(pk=tag.pk)
        self.assertEqual(found.note_count, 3)

    def test_showall_controls_status_filtering(self):
        tag = self.make_tag(name="closed-tag")
        closed_task = self.make_task(title="Closed", status="closed", due_date=None)
        self.tag_note(closed_task, tag)

        hidden = self._get(showall=False)
        self.assertNotIn(tag, hidden.context["tags_undated"])

        shown = self._get(showall=True)
        self.assertIn(tag, shown.context["tags_undated"])

    def test_only_current_users_tags_are_shown(self):
        other_tag = self.make_tag(user=self.other_user, name="not-mine")
        other_task = self.make_task(user=self.other_user, title="Not mine", due_date=None)
        self.tag_note(other_task, other_tag)

        resp = self._get()

        self.assertNotIn(other_tag, resp.context["tags_undated"])
