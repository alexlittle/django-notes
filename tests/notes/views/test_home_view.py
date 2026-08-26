from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse

from tests.base import TODAY, NotesTestCase


def _get(client, showall=False):
    with (
        patch("notes.views.get_user_aware_date", return_value=TODAY),
        patch("notes.views.is_showall", return_value=showall),
    ):
        return client.get(reverse("notes:home"))


class HomeViewTests(NotesTestCase):
    def test_tasks_are_bucketed_by_due_date(self):
        overdue = self.make_task(title="Overdue", due_date=TODAY - timedelta(days=2))
        today = self.make_task(title="Today", due_date=TODAY)
        tomorrow = self.make_task(title="Tomorrow", due_date=TODAY + timedelta(days=1))
        next_week = self.make_task(title="Next week", due_date=TODAY + timedelta(days=5))
        next_month = self.make_task(title="Next month", due_date=TODAY + timedelta(days=20))
        far_future = self.make_task(title="Far future", due_date=TODAY + timedelta(days=60))

        resp = _get(self.client)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context["overdue"]), [overdue])
        self.assertEqual(list(resp.context["today"]), [today])
        self.assertEqual(list(resp.context["tomorrow"]), [tomorrow])
        self.assertEqual(list(resp.context["next_week"]), [next_week])
        self.assertEqual(list(resp.context["next_month"]), [next_month])
        for bucket in ("overdue", "today", "tomorrow", "next_week", "next_month"):
            self.assertNotIn(far_future, resp.context[bucket])

    def test_non_task_notes_are_never_bucketed(self):
        self.make_note(type="bookmark", title="Bookmark", due_date=TODAY)
        self.make_note(type="idea", title="Idea", due_date=TODAY)

        resp = _get(self.client)

        for bucket in ("overdue", "today", "tomorrow", "next_week", "next_month"):
            self.assertEqual(len(resp.context[bucket]), 0)

    def test_undated_tasks_are_excluded(self):
        self.make_task(title="No due date", due_date=None)

        resp = _get(self.client)

        for bucket in ("overdue", "today", "tomorrow", "next_week", "next_month"):
            self.assertEqual(len(resp.context[bucket]), 0)

    def test_only_current_users_tasks_are_shown(self):
        self.make_task(user=self.other_user, title="Not mine", due_date=TODAY)

        resp = _get(self.client)

        self.assertEqual(len(resp.context["today"]), 0)

    def test_showall_controls_whether_completed_tasks_appear(self):
        completed = self.make_task(title="Done", due_date=TODAY, status="completed")

        hidden = _get(self.client, showall=False)
        self.assertNotIn(completed, hidden.context["today"])

        shown = _get(self.client, showall=True)
        self.assertIn(completed, shown.context["today"])
        self.assertTrue(shown.context["showall"])

    def test_closed_and_archived_tasks_are_always_excluded(self):
        self.make_task(title="Closed", due_date=TODAY, status="closed")
        self.make_task(title="Archived", due_date=TODAY, status="archived")

        resp = _get(self.client, showall=True)

        self.assertEqual(len(resp.context["today"]), 0)

    def test_reminder_only_includes_tasks_inside_their_reminder_window(self):
        # due in 3 days, reminder_days=5 -> threshold = today-2 -> today > threshold: included
        due_soon = self.make_task(
            title="Remind me", due_date=TODAY + timedelta(days=3), reminder_days=5
        )
        # due in 3 days, reminder_days=1 -> threshold = today+2 -> today > threshold is False
        too_early = self.make_task(
            title="Not yet", due_date=TODAY + timedelta(days=3), reminder_days=1
        )
        # reminder_days unset -> excluded by the underlying queryset filter itself
        no_reminder = self.make_task(title="No reminder set", due_date=TODAY + timedelta(days=3))
        # due date already in the past -> due_date > now.date() is False
        already_due = self.make_task(
            title="Already due", due_date=TODAY - timedelta(days=1), reminder_days=10
        )

        resp = _get(self.client)

        self.assertIn(due_soon, resp.context["reminder"])
        self.assertNotIn(too_early, resp.context["reminder"])
        self.assertNotIn(no_reminder, resp.context["reminder"])
        self.assertNotIn(already_due, resp.context["reminder"])
