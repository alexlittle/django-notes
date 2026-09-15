from datetime import timedelta
from unittest.mock import Mock, patch
from urllib import error

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from notes.models import Note, NotesConfig

from .base import NotesCommandTestCase


class LinkCheckerCommandTests(NotesCommandTestCase):
    def setUp(self):
        super().setUp()
        # Retries/consecutive-failure handling sleep between attempts - skip
        # the real delay so these tests stay fast.
        sleep_patcher = patch("notes.management.commands.link_checker.time.sleep")
        sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)

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

    def test_limit_checks_only_the_oldest_checked_links(self):
        oldest = self._make_link(
            url="https://oldest.example.com",
            link_check_date=timezone.now() - timedelta(days=30),
        )
        middle = self._make_link(
            url="https://middle.example.com",
            link_check_date=timezone.now() - timedelta(days=20),
        )
        newest = self._make_link(
            url="https://newest.example.com",
            link_check_date=timezone.now() - timedelta(days=10),
        )

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0, limit=2)

        self.assertEqual(mocked.call_count, 2)
        oldest.refresh_from_db()
        middle.refresh_from_db()
        newest.refresh_from_db()
        self.assertEqual(oldest.link_check_result, "ok")
        self.assertEqual(middle.link_check_result, "ok")
        self.assertEqual(newest.link_check_result, "")

    def test_no_limit_checks_every_due_link(self):
        self._make_link(url="https://one.example.com")
        self._make_link(url="https://two.example.com")

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        self.assertEqual(mocked.call_count, 2)

    def test_a_successful_response_is_recorded_as_ok(self):
        note = self._make_link()

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "ok")

    def test_a_successful_check_resets_the_consecutive_failure_count(self):
        note = self._make_link(link_check_fail_count=3)

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "ok")
        self.assertEqual(note.link_check_fail_count, 0)

    def test_a_single_failure_is_not_yet_reported_or_offered_for_deletion(self):
        note = self._make_link()
        self._enable_email()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=TimeoutError,
            ),
            patch("builtins.input") as mocked_input,
        ):
            call_command("link_checker", 0)

        mocked_input.assert_not_called()
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "error")
        self.assertEqual(note.link_check_fail_count, 1)
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_transient_errors_are_retried_before_being_recorded_as_an_error(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=[TimeoutError(), ConnectionResetError(), Mock(code=200)],
            ) as mocked,
        ):
            call_command("link_checker", 0)

        self.assertEqual(mocked.call_count, 3)
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "ok")

    def test_a_5xx_response_is_retried(self):
        note = self._make_link()

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=[
                    error.HTTPError(note.url, 503, "Service Unavailable", None, None),
                    Mock(code=200),
                ],
            ) as mocked,
        ):
            call_command("link_checker", 0)

        self.assertEqual(mocked.call_count, 2)
        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "ok")

    def test_connection_style_errors_offer_deletion_after_two_consecutive_failures(self):
        note = self._make_link(link_check_fail_count=1)

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
        note = self._make_link(link_check_fail_count=1)

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
        self.assertEqual(note.link_check_fail_count, 2)

    def test_noinput_records_errors_without_prompting_or_deleting(self):
        note = self._make_link(link_check_fail_count=1)

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
        note = self._make_link(link_check_fail_count=1)

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.HTTPError(note.url, 404, "Not Found", None, None),
            ),
            patch("builtins.input", return_value="n"),
        ):
            call_command("link_checker", 0)

        note.refresh_from_db()
        self.assertEqual(note.link_check_result, "error")

    def test_generic_url_errors_are_recorded_as_an_error_and_deletion_is_offered(self):
        note = self._make_link(link_check_fail_count=1)

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

    def test_403_and_429_responses_are_recorded_as_blocked_not_error(self):
        forbidden = self._make_link(url="https://forbidden.example.com")
        rate_limited = self._make_link(url="https://ratelimited.example.com")

        def fake_urlopen(req, timeout=20):
            if req.full_url == forbidden.url:
                raise error.HTTPError(forbidden.url, 403, "Forbidden", None, None)
            raise error.HTTPError(rate_limited.url, 429, "Too Many Requests", None, None)

        with patch(
            "notes.management.commands.link_checker.request.urlopen",
            side_effect=fake_urlopen,
        ):
            call_command("link_checker", 0)

        forbidden.refresh_from_db()
        rate_limited.refresh_from_db()
        self.assertEqual(forbidden.link_check_result, "blocked")
        self.assertEqual(rate_limited.link_check_result, "blocked")

    def test_blocked_links_are_never_offered_for_deletion_even_after_repeated_failures(self):
        note = self._make_link(link_check_fail_count=5)

        with (
            patch(
                "notes.management.commands.link_checker.request.urlopen",
                side_effect=error.HTTPError(note.url, 403, "Forbidden", None, None),
            ),
            patch("builtins.input") as mocked_input,
        ):
            call_command("link_checker", 0)

        mocked_input.assert_not_called()
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())

    def _check_one_broken_and_one_redirected_link(self):
        broken = self._make_link(url="https://broken.example.com", link_check_fail_count=1)
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

    def test_blocked_links_appear_in_the_report_email_in_their_own_section(self):
        self._enable_email()
        note = self._make_link(url="https://blocked.example.com", link_check_fail_count=1)

        with patch(
            "notes.management.commands.link_checker.request.urlopen",
            side_effect=error.HTTPError(note.url, 403, "Forbidden", None, None),
        ):
            call_command("link_checker", 0)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(note.url, sent.body)
        self.assertIn("Blocked", sent.body)

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

    def test_the_report_includes_previously_flagged_links_even_when_not_rechecked_this_run(self):
        self._enable_email()
        already_flagged = self._make_link(
            url="https://already-broken.example.com",
            link_check_result="error",
            link_check_fail_count=2,
            link_check_date=timezone.now(),
        )
        ok_note = self._make_link(
            url="https://ok.example.com",
            link_check_date=timezone.now() - timedelta(days=10),
        )

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0, limit=1)

        # Only the oldest-checked note (ok_note) was actually re-checked this run...
        mocked.assert_called_once()
        ok_note.refresh_from_db()
        self.assertEqual(ok_note.link_check_result, "ok")

        # ...but the digest still reports the link flagged by an earlier run.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(already_flagged.url, mail.outbox[0].body)
        self.assertNotIn(ok_note.url, mail.outbox[0].body)

    def test_no_email_is_sent_when_the_configured_interval_has_not_elapsed(self):
        self._enable_email()
        NotesConfig.objects.update_or_create(
            name="link_check.email_last_sent_at",
            defaults={"value": (timezone.now() - timedelta(hours=1)).isoformat()},
        )

        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 0)

    def test_email_is_sent_again_once_the_configured_interval_has_elapsed(self):
        self._enable_email()
        NotesConfig.objects.update_or_create(
            name="link_check.email_last_sent_at",
            defaults={"value": (timezone.now() - timedelta(hours=25)).isoformat()},
        )

        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 1)

    def test_the_configured_interval_can_be_shortened(self):
        self._enable_email()
        NotesConfig.objects.update_or_create(
            name="link_check.email_interval_hours", defaults={"value": "1"}
        )
        NotesConfig.objects.update_or_create(
            name="link_check.email_last_sent_at",
            defaults={"value": (timezone.now() - timedelta(hours=2)).isoformat()},
        )

        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 1)

    def test_an_invalid_interval_configuration_falls_back_to_the_24_hour_default(self):
        self._enable_email()
        NotesConfig.objects.update_or_create(
            name="link_check.email_interval_hours", defaults={"value": "not-a-number"}
        )
        NotesConfig.objects.update_or_create(
            name="link_check.email_last_sent_at",
            defaults={"value": (timezone.now() - timedelta(hours=1)).isoformat()},
        )

        self._check_one_broken_and_one_redirected_link()

        self.assertEqual(len(mail.outbox), 0)

    def test_last_sent_at_is_recorded_after_a_successful_send(self):
        self._enable_email()

        self._check_one_broken_and_one_redirected_link()

        self.assertNotEqual(NotesConfig.get_value("link_check.email_last_sent_at"), "")

    def test_last_sent_at_is_not_updated_when_there_is_nothing_to_report(self):
        self._enable_email()
        self._make_link()

        with patch("notes.management.commands.link_checker.request.urlopen") as mocked:
            mocked.return_value.code = 200
            call_command("link_checker", 0)

        self.assertEqual(NotesConfig.get_value("link_check.email_last_sent_at"), "")
