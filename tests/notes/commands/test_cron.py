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

    def test_old_closed_tasks_are_deleted_based_on_update_date(self):
        # Note.close_task() never sets completed_date (a closed task was
        # never completed), so the cleanup has to key off update_date -
        # same as the archived-tasks branch just below it.
        self._set_config("retain.days", "31")
        closed_task = self.make_note(type="task", title="Closed the normal way", status="open")
        closed_task.close_task()
        Note.objects.filter(pk=closed_task.pk).update(
            update_date=timezone.now() - timedelta(days=40)
        )

        _run_cron()

        self.assertFalse(Note.objects.filter(pk=closed_task.pk).exists())

    def test_recently_closed_tasks_are_not_cleaned_up(self):
        self._set_config("retain.days", "31")
        closed_task = self.make_note(type="task", title="Closed recently", status="open")
        closed_task.close_task()

        _run_cron()

        self.assertTrue(Note.objects.filter(pk=closed_task.pk).exists())

    def test_delegates_to_link_checker_non_interactively_with_default_stale_days(self):
        self._clear_config("link_check.days")
        mocked = _run_cron()

        link_checker_calls = [c for c in mocked.call_args_list if c.args[0] == "link_checker"]
        self.assertEqual(len(link_checker_calls), 1)
        self.assertEqual(link_checker_calls[0].args[1], 7)
        self.assertEqual(link_checker_calls[0].kwargs.get("interactive"), False)

    def test_uses_the_configured_link_check_days_when_present(self):
        self._set_config("link_check.days", "3")
        mocked = _run_cron()

        link_checker_calls = [c for c in mocked.call_args_list if c.args[0] == "link_checker"]
        self.assertEqual(link_checker_calls[0].args[1], 3)

    def test_defaults_link_check_batch_size_to_50_when_config_is_missing(self):
        self._clear_config("link_check.batch_size")
        mocked = _run_cron()

        link_checker_calls = [c for c in mocked.call_args_list if c.args[0] == "link_checker"]
        self.assertEqual(link_checker_calls[0].kwargs.get("limit"), 50)

    def test_uses_the_configured_link_check_batch_size_when_present(self):
        self._set_config("link_check.batch_size", "5")
        mocked = _run_cron()

        link_checker_calls = [c for c in mocked.call_args_list if c.args[0] == "link_checker"]
        self.assertEqual(link_checker_calls[0].kwargs.get("limit"), 5)
