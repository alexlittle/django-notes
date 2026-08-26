from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

from notes.models import Note, NotesConfig

from .base import NotesCommandTestCase


def _run_cron():
    with patch("notes.management.commands.cron.call_command") as mocked_subcommands:
        call_command("cron")
    return mocked_subcommands


class CronCommandTests(NotesCommandTestCase):
    @staticmethod
    def _set_config(name, value):
        NotesConfig.objects.update_or_create(name=name, defaults={"value": value})

    @staticmethod
    def _clear_config(name):
        NotesConfig.objects.filter(name=name).delete()

    def test_delegates_to_clean_tags_and_build_tag_suggestions(self):
        mocked = _run_cron()

        called_commands = [c.args[0] for c in mocked.call_args_list]
        self.assertIn("clean_tags", called_commands)
        self.assertIn("build_tag_suggestions", called_commands)

    def test_defaults_retention_to_31_days_when_config_is_missing(self):
        self._clear_config("retain.days")
        old_enough = self.make_note(
            type="task",
            title="Old completed",
            status="completed",
            completed_date=timezone.now().date() - timedelta(days=32),
        )
        too_recent = self.make_note(
            type="task",
            title="Recently completed",
            status="completed",
            completed_date=timezone.now().date() - timedelta(days=30),
        )

        _run_cron()

        self.assertFalse(Note.objects.filter(pk=old_enough.pk).exists())
        self.assertTrue(Note.objects.filter(pk=too_recent.pk).exists())

    def test_uses_the_configured_retain_days_when_present(self):
        self._set_config("retain.days", "10")
        old_enough = self.make_note(
            type="task",
            title="Old completed",
            status="completed",
            completed_date=timezone.now().date() - timedelta(days=11),
        )
        too_recent = self.make_note(
            type="task",
            title="Recently completed",
            status="completed",
            completed_date=timezone.now().date() - timedelta(days=9),
        )

        _run_cron()

        self.assertFalse(Note.objects.filter(pk=old_enough.pk).exists())
        self.assertTrue(Note.objects.filter(pk=too_recent.pk).exists())

    def test_only_task_type_notes_are_ever_cleaned_up(self):
        old_bookmark = self.make_note(
            type="bookmark",
            title="Old bookmark",
            status="completed",
            completed_date=timezone.now().date() - timedelta(days=100),
        )

        _run_cron()

        self.assertTrue(Note.objects.filter(pk=old_bookmark.pk).exists())

    def test_old_archived_tasks_are_deleted_based_on_update_date(self):
        self._set_config("retain.days", "31")
        old_archived = self.make_note(
            type="task",
            title="Old archived",
            status="archived",
            update_date=timezone.now() - timedelta(days=40),
        )

        _run_cron()

        self.assertFalse(Note.objects.filter(pk=old_archived.pk).exists())

    def test_closed_tasks_produced_by_close_task_are_never_cleaned_up(self):
        # Note.close_task() always sets completed_date to None. The cron
        # command's "old closed tasks" cleanup filters on
        # completed_date__lte=<cutoff>, which can never match a NULL
        # value in SQL - so tasks closed the normal way are never actually
        # eligible for this cleanup, no matter how old update_date is.
        closed_task = self.make_note(type="task", title="Closed the normal way", status="open")
        closed_task.close_task()
        Note.objects.filter(pk=closed_task.pk).update(
            update_date=timezone.now() - timedelta(days=100)
        )

        _run_cron()

        self.assertTrue(Note.objects.filter(pk=closed_task.pk).exists())

    def test_closed_tasks_are_only_removed_if_completed_date_happens_to_be_set(self):
        # Demonstrates the branch does work when completed_date is present -
        # it just never naturally ends up that way via close_task().
        self._set_config("retain.days", "31")
        closed_task = self.make_note(
            type="task",
            title="Closed with a completed_date",
            status="closed",
            completed_date=timezone.now().date() - timedelta(days=100),
        )

        _run_cron()

        self.assertFalse(Note.objects.filter(pk=closed_task.pk).exists())
