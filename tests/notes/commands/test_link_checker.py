from datetime import timedelta
from unittest.mock import patch
from urllib import error

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from notes.models import Note, NotesConfig

from .base import NotesCommandTestCase


class LinkCheckerCommandTests(NotesCommandTestCase):
    def _make_link(self, url="https://example.com", **kwargs):
        return self.make_note(type="bookmark", title="A link", url=url, **kwargs)

    @staticmethod
    def _enable_email(recipients=None):
        NotesConfig.objects.update_or_create(
            name="link_check.email_enabled", defaults={"value": "true"}
        )
        if recipients is not None:
            NotesConfig.objects.update_or_create(
                name="link_check.email_recipients", defaults={"value": recipients}
            )

    def test_notes_without_a_url_are_never_checked(self):
        # Note.url has no null=True any more (backed by a NOT NULL column),
        # so an empty string is the only way a bookmark can be without a URL.
        blank_url = self._make_link(url="")

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            call_command("link_checker", 0)

        mocked.assert_not_called()
        blank_url.refresh_from_db()
        self.assertEqual(blank_url.link_check_result, "")

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
        self.assertEqual(fresh.link_check_result, "")

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

    def test_noinput_records_errors_without_prompting_or_deleting(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=TimeoutError,
            ),
            patch("builtins.input") as mocked_input,
        ):
            call_command("link_checker", 0, interactive=False)

        mocked_input.assert_not_called()
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "error")
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())

    def test_actual_redirect_status_codes_are_recorded_as_redirect_without_a_deletion_prompt(
        self,
    ):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.HTTPError(note.url, 301, "Moved Permanently", None, None),
            ),
            patch("builtins.input") as mocked_input,
        ):
            call_command("link_checker", 0)

        mocked_input.assert_not_called()
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "redirect")

    def test_redirects_are_still_checked_but_excluded_from_the_report_when_ignored(self):
        note = self._make_link(link_check_ignore_redirects=True)
        self._enable_email()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.HTTPError(note.url, 301, "Moved Permanently", None, None),
            ),
            patch("builtins.input") as mocked_input,
        ):
            call_command("link_checker", 0)

        mocked_input.assert_not_called()
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "redirect")
        self.assertEqual(len(mail.outbox), 0)

    def test_non_redirect_http_errors_are_recorded_as_an_error_and_deletion_is_offered(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.HTTPError(note.url, 403, "Forbidden", None, None),
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "error")

    def test_generic_url_errors_are_recorded_as_an_error_and_deletion_is_offered(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.URLError("boom"),
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "error")

    def _check_one_broken_and_one_redirected_link(self):
        broken = self._make_link(url="https://broken.example.com")
        redirected = self._make_link(url="https://redirected.example.com")

        def fake_urlopen(req, timeout=20):
            if req.full_url == broken.url:
                raise TimeoutError
            raise error.HTTPError(redirected.url, 301, "Moved Permanently", None, None)

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=fake_urlopen,
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("link_checker", 0)

        return broken, redirected

    def test_no_email_is_sent_by_default_even_when_links_are_broken(self):
        # link_check.email_enabled is unset - email is off by default until
        # someone turns it on via NotesConfig.
        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 0)

    def test_no_email_is_sent_when_explicitly_disabled_via_notesconfig(self):
        NotesConfig.objects.update_or_create(
            name="link_check.email_enabled", defaults={"value": "false"}
        )
        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 0)

    def test_broken_and_redirected_links_trigger_a_report_email_when_enabled(self):
        self._enable_email()
        broken, redirected = self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(broken.url, sent.body)
        self.assertIn(redirected.url, sent.body)
        html_body, _mimetype = sent.alternatives[0]
        self.assertIn(broken.url, html_body)
        self.assertIn(redirected.url, html_body)

    def test_email_goes_to_the_admins_by_default_when_no_recipients_are_configured(self):
        self._enable_email()
        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(mail.outbox[0].to, [addr for _name, addr in settings.ADMINS])

    def test_email_uses_the_configured_recipients(self):
        self._enable_email(recipients="a@example.com, b@example.com")
        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(mail.outbox[0].to, ["a@example.com", "b@example.com"])

    def test_no_email_is_sent_when_every_link_is_ok(self):
        self._enable_email()
        self._make_link()

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        self.assertEqual(len(mail.outbox), 0)
