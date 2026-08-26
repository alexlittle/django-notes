from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse

from tests.base import TODAY, NotesTestCase


def _get(client, showall=False):
    with (
        patch("notes.views.get_user_aware_date", return_value=TODAY),
        patch("notes.views.is_showall", return_value=showall),
    ):
        return client.get(reverse("notes:tasks_future"))


class FutureTasksViewTests(NotesTestCase):
    def test_only_tasks_more_than_31_days_out_are_included(self):
        within_month = self.make_task(title="Within a month", due_date=TODAY + timedelta(days=31))
        just_future = self.make_task(title="Just future", due_date=TODAY + timedelta(days=32))
        far_future = self.make_task(title="Far future", due_date=TODAY + timedelta(days=200))

        resp = _get(self.client)

        self.assertEqual(resp.status_code, 200)
        future = list(resp.context["future"])
        self.assertNotIn(within_month, future)
        self.assertIn(just_future, future)
        self.assertIn(far_future, future)
        # ordered by due_date ascending
        self.assertEqual(future, [just_future, far_future])

    def test_undated_and_non_task_notes_excluded(self):
        self.make_task(title="No date", due_date=None)
        self.make_note(type="bookmark", title="Bookmark", due_date=TODAY + timedelta(days=100))

        resp = _get(self.client)

        self.assertEqual(len(resp.context["future"]), 0)

    def test_showall_controls_completed_visibility(self):
        completed = self.make_task(
            title="Done", due_date=TODAY + timedelta(days=100), status="completed"
        )

        hidden = _get(self.client, showall=False)
        self.assertNotIn(completed, hidden.context["future"])

        shown = _get(self.client, showall=True)
        self.assertIn(completed, shown.context["future"])
