from datetime import timedelta
from unittest.mock import patch
from urllib import error

from django.core.management import call_command
from django.utils import timezone

from notes.models import Note

from .base import NotesCommandTestCase


class LinkCheckerCommandTests(NotesCommandTestCase):
    def _make_link(self, url="https://example.com", **kwargs):
        return self.make_note(type="bookmark", title="A link", url=url, **kwargs)

    def test_notes_without_a_url_are_never_checked(self):
        # Note.url has no null=True any more (backed by a NOT NULL column),
        # so an empty string is the only way a bookmark can be without a URL.
        blank_url = self._make_link(url="")

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            call_command("link_checker", 0)

        mocked.assert_not_called()
        blank_url.refresh_from_db()
        self.assertIsNone(blank_url.link_check_result)

    def test_days_zero_checks_every_url_regardless_of_last_check_date(self):
        note = self._make_link(link_check_date=timezone.now() - timedelta(days=1000))

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        mocked.assert_called_once()
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "ok")

    def test_a_positive_days_value_only_rechecks_stale_links(self):
        stale = self._make_link(
            url="https://stale.example.com",
            link_check_date=timezone.now() - timedelta(days=10),
        )
        fresh = self._make_link(
            url="https://fresh.example.com",
            link_check_date=timezone.now() - timedelta(days=1),
        )

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 5)

        mocked.assert_called_once()
        stale.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(stale.link_check_result, "ok")
        self.assertIsNone(fresh.link_check_result)

    def test_a_successful_response_is_recorded_as_ok(self):
        note = self._make_link()

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "ok")

    def test_connection_style_errors_are_recorded_and_deletion_is_offered(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=TimeoutError,
            ),
            patch("builtins.input", return_value="y") as mocked_input,
        ):
            call_command("link_checker", 0)

        mocked_input.assert_called_once()
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_declining_deletion_keeps_the_note_marked_as_an_error(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=ConnectionResetError,
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "error")

    def test_url_errors_are_recorded_as_redirect_without_a_deletion_prompt(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.URLError("boom"),
            ),
            patch("builtins.input") as mocked_input,
        ):
            call_command("link_checker", 0)

        mocked_input.assert_not_called()
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "redirect")
