from datetime import timedelta

from django.urls import reverse

from notes.models import NotesConfig
from tests.base import TODAY, NotesTestCase


class ScheduleViewTests(NotesTestCase):
    def setUp(self):
        super().setUp()
        # update_or_create rather than create(): the test DB already seeds
        # some NotesConfig rows (via a data migration), so a plain create()
        # here would leave two rows with the same `name` and make
        # NotesConfig.get_value()'s .get() raise MultipleObjectsReturned.
        self._set_config("schedule.start.days", "7")
        self._set_config("schedule.end.days", "7")

    @staticmethod
    def _set_config(name, value):
        NotesConfig.objects.update_or_create(name=name, defaults={"value": value})

    def test_builds_one_row_per_configured_tag_group(self):
        self.make_tag(name="work", label="Work")
        self.make_tag(name="urgent", label="Urgent")
        self._set_config("schedule.tags", "work,work+urgent")

        resp = self.client.get(reverse("notes:schedule"))

        self.assertEqual(resp.status_code, 200)
        row_keys = {row["key"] for row in resp.context["row_tags"]}
        self.assertEqual(row_keys, {"work", "work+urgent"})

    def test_blank_entries_in_schedule_tags_are_skipped(self):
        self.make_tag(name="work", label="Work")
        self._set_config("schedule.tags", "work,,  ,")

        resp = self.client.get(reverse("notes:schedule"))

        self.assertEqual(len(resp.context["row_tags"]), 1)

    def test_a_task_only_appears_in_a_row_if_it_has_every_tag_in_that_row(self):
        work = self.make_tag(name="work", label="Work")
        urgent = self.make_tag(name="urgent", label="Urgent")
        self._set_config("schedule.tags", "work+urgent")

        both_tags = self.make_task(title="Both", due_date=TODAY, status="open")
        self.tag_note(both_tags, work)
        self.tag_note(both_tags, urgent)

        only_work = self.make_task(title="Only work", due_date=TODAY, status="open")
        self.tag_note(only_work, work)

        resp = self.client.get(reverse("notes:schedule"))

        grid = resp.context["grid"]["work+urgent"]
        all_tasks_shown = [t for week in grid for t in week["tasks"]]
        self.assertIn(both_tags, all_tasks_shown)
        self.assertNotIn(only_work, all_tasks_shown)

    def test_tasks_outside_the_visible_date_range_are_excluded(self):
        tag = self.make_tag(name="work", label="Work")
        self._set_config("schedule.tags", "work")

        far_future = self.make_task(
            title="Way off", due_date=TODAY + timedelta(days=365), status="open"
        )
        self.tag_note(far_future, tag)

        resp = self.client.get(reverse("notes:schedule"))

        grid = resp.context["grid"]["work"]
        all_tasks_shown = [t for week in grid for t in week["tasks"]]
        self.assertNotIn(far_future, all_tasks_shown)

    def test_closed_and_archived_tasks_are_never_shown(self):
        tag = self.make_tag(name="work", label="Work")
        self._set_config("schedule.tags", "work")

        closed = self.make_task(title="Closed", due_date=TODAY, status="closed")
        self.tag_note(closed, tag)

        resp = self.client.get(reverse("notes:schedule"))

        grid = resp.context["grid"]["work"]
        all_tasks_shown = [t for week in grid for t in week["tasks"]]
        self.assertNotIn(closed, all_tasks_shown)

    def test_row_label_falls_back_to_slug_when_tag_has_no_label(self):
        self.make_tag(name="nolabel", label="")
        self._set_config("schedule.tags", "nolabel")

        resp = self.client.get(reverse("notes:schedule"))

        row = resp.context["row_tags"][0]
        self.assertEqual(row["label"], "nolabel")

    def test_rows_are_sorted_by_first_label_case_insensitively(self):
        self.make_tag(name="zeta", label="zeta")
        self.make_tag(name="alpha", label="Alpha")
        self._set_config("schedule.tags", "zeta,alpha")

        resp = self.client.get(reverse("notes:schedule"))

        labels = [row["first_label"] for row in resp.context["row_tags"]]
        self.assertEqual(labels, ["Alpha", "zeta"])

    def test_current_week_is_flagged(self):
        self._set_config("schedule.tags", "")

        resp = self.client.get(reverse("notes:schedule"))

        current_weeks = [w for w in resp.context["weeks"] if w["is_current"]]
        self.assertEqual(len(current_weeks), 1)

    def test_schedule_is_not_scoped_to_the_current_user(self):
        # Unlike most other views here, ScheduleView's Tag/Note queries have
        # no user= filter at all, so it shows tasks across every user. This
        # test documents that as current behaviour - see README.
        tag = self.make_tag(user=self.other_user, name="work", label="Work")
        self._set_config("schedule.tags", "work")

        other_users_task = self.make_task(
            user=self.other_user, title="Someone else's", due_date=TODAY, status="open"
        )
        self.tag_note(other_users_task, tag)

        resp = self.client.get(reverse("notes:schedule"))

        grid = resp.context["grid"]["work"]
        all_tasks_shown = [t for week in grid for t in week["tasks"]]
        self.assertIn(other_users_task, all_tasks_shown)
