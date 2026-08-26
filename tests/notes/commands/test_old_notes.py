from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.core.management import call_command
from django.utils import timezone

from notes.models import Note

from .base import NotesCommandTestCase


class OldNotesCommandTests(NotesCommandTestCase):
    def _make_note_years_ago(self, years, **kwargs):
        return self.make_note(
            title=f"{years}y old",
            create_date=timezone.now() - relativedelta(years=years),
            **kwargs,
        )

    def test_only_notes_within_the_year_window_are_prompted_for(self):
        too_recent = self._make_note_years_ago(0)
        in_window = self._make_note_years_ago(2)
        too_old = self._make_note_years_ago(5)

        with patch("builtins.input", return_value="n") as mocked_input:
            call_command("old_notes", 1, 3)  # window: 1-4 years ago

        mocked_input.assert_called_once()
        for note in (too_recent, in_window, too_old):
            self.assertTrue(Note.objects.filter(pk=note.pk).exists())

    def test_accepting_deletion_removes_the_note(self):
        note = self._make_note_years_ago(2)

        with patch("builtins.input", return_value="y"):
            call_command("old_notes", 1, 3)

        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_declining_deletion_keeps_the_note(self):
        note = self._make_note_years_ago(2)

        with patch("builtins.input", return_value="n"):
            call_command("old_notes", 1, 3)

        self.assertTrue(Note.objects.filter(pk=note.pk).exists())

    def test_window_boundaries_are_inclusive(self):
        # Freeze "now" for the command itself, and build the boundary
        # notes off that exact same value - otherwise the command's own
        # timezone.now() call (a moment later than the test's) shifts the
        # cutoffs forward by a hair and makes an inclusive boundary look
        # exclusive.
        start_years, no_years = 1, 2
        frozen_now = timezone.now()
        at_start_boundary = self.make_note(
            title="At start boundary",
            create_date=frozen_now - relativedelta(years=start_years),
        )
        at_end_boundary = self.make_note(
            title="At end boundary",
            create_date=frozen_now - relativedelta(years=start_years + no_years),
        )

        with (
            patch("notes.management.commands.old_notes.timezone.now", return_value=frozen_now),
            patch("builtins.input", return_value="n") as mocked_input,
        ):
            call_command("old_notes", start_years, no_years)

        self.assertEqual(mocked_input.call_count, 2)
        self.assertTrue(Note.objects.filter(pk=at_start_boundary.pk).exists())
        self.assertTrue(Note.objects.filter(pk=at_end_boundary.pk).exists())
