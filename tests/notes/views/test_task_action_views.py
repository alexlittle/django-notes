from datetime import timedelta

from django.urls import reverse

from notes.models import Note
from tests.base import TODAY, NotesTestCase


class CompleteTaskViewTests(NotesTestCase):
    def test_completes_a_non_recurring_task(self):
        task = self.make_task(title="Do it", due_date=TODAY, recurrence=None)

        resp = self.client.get(reverse("notes:complete_task", kwargs={"note_id": task.pk}))

        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertIsNotNone(task.completed_date)
        self.assertRedirects(resp, reverse("notes:home"), fetch_redirect_response=False)

    def test_completing_a_recurring_task_archives_it_and_creates_the_next_one(self):
        task = self.make_task(
            title="Water plants", due_date=TODAY, recurrence="weekly", priority="low"
        )

        self.client.get(reverse("notes:complete_task", kwargs={"note_id": task.pk}))

        task.refresh_from_db()
        self.assertEqual(task.status, "archived")

        next_task = Note.objects.exclude(pk=task.pk).get(title="Water plants")
        self.assertEqual(next_task.due_date, TODAY + timedelta(weeks=1))
        self.assertEqual(next_task.status, "open")
        self.assertEqual(next_task.recurrence, "weekly")

    def test_redirects_to_referer_when_present(self):
        task = self.make_task(title="Do it", due_date=TODAY)

        resp = self.client.get(
            reverse("notes:complete_task", kwargs={"note_id": task.pk}),
            HTTP_REFERER="/notes/tasks/",
        )

        self.assertRedirects(resp, "/notes/tasks/", fetch_redirect_response=False)

    def test_cannot_complete_another_users_task(self):
        task = self.make_task(user=self.other_user, title="Not mine", due_date=TODAY)

        with self.assertRaises(Note.DoesNotExist):
            self.client.get(reverse("notes:complete_task", kwargs={"note_id": task.pk}))


class UnCompleteTaskViewTests(NotesTestCase):
    def test_reopens_a_completed_task(self):
        task = self.make_task(
            title="Oops", due_date=TODAY, status="completed", completed_date=TODAY
        )

        self.client.get(reverse("notes:uncomplete_task", kwargs={"note_id": task.pk}))

        task.refresh_from_db()
        self.assertEqual(task.status, "open")
        self.assertIsNone(task.completed_date)


class CloseTaskViewTests(NotesTestCase):
    def test_closes_a_task(self):
        task = self.make_task(title="Never mind", due_date=TODAY, status="open")

        self.client.get(reverse("notes:close_task", kwargs={"note_id": task.pk}))

        task.refresh_from_db()
        self.assertEqual(task.status, "closed")
        self.assertIsNone(task.completed_date)
