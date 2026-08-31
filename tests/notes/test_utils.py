"""Tests for notes.utils."""

import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.test import RequestFactory, override_settings
from django.utils import timezone

from notes.models import NotesProfile
from notes.utils import (
    get_filtered_notes,
    get_user_aware_date,
    get_user_aware_datetime,
    is_showall,
    send_templated_mail,
)
from tests.base import NotesTestCase


class GetUserAwareDatetimeTests(NotesTestCase):
    def test_anonymous_user_falls_back_to_django_current_time(self):
        before = timezone.now()
        result = get_user_aware_datetime(AnonymousUser())
        after = timezone.now()

        assert before <= result <= after

    def test_authenticated_user_without_a_profile_falls_back_to_django_current_time(self):
        # NotesProfile is only created by the admin/an explicit save, so a
        # freshly created user has none - user.profile raises AttributeError.
        assert not hasattr(self.user, "profile")

        before = timezone.now()
        result = get_user_aware_datetime(self.user)
        after = timezone.now()

        assert before <= result <= after

    def test_authenticated_user_with_a_valid_timezone_gets_that_timezone(self):
        NotesProfile.objects.create(user=self.user, timezone="America/New_York")

        result = get_user_aware_datetime(self.user)

        assert result.tzinfo == ZoneInfo("America/New_York")

    def test_authenticated_user_with_an_invalid_timezone_falls_back_to_django_current_time(self):
        NotesProfile.objects.create(user=self.user, timezone="Not/A_Real_Zone")

        before = timezone.now()
        result = get_user_aware_datetime(self.user)
        after = timezone.now()

        assert before <= result <= after


class GetUserAwareDateTests(NotesTestCase):
    def test_returns_the_date_component_of_the_user_aware_datetime(self):
        NotesProfile.objects.create(user=self.user, timezone="America/New_York")
        expected = datetime.datetime.now(ZoneInfo("America/New_York")).date()

        assert get_user_aware_date(self.user) == expected


class TestIsShowall:
    factory = RequestFactory()

    def test_defaults_to_false_when_param_is_missing(self):
        request = self.factory.get("/")

        assert is_showall(request) is False

    def test_true_when_param_is_true(self):
        request = self.factory.get("/", {"showall": "true"})

        assert is_showall(request) is True

    def test_true_is_case_insensitive(self):
        request = self.factory.get("/", {"showall": "TRUE"})

        assert is_showall(request) is True

    def test_false_when_param_is_explicitly_false(self):
        request = self.factory.get("/", {"showall": "false"})

        assert is_showall(request) is False

    def test_any_other_value_counts_as_true(self):
        request = self.factory.get("/", {"showall": "yes"})

        assert is_showall(request) is True


class GetFilteredNotesTests(NotesTestCase):
    def test_returns_notes_matching_a_single_tag(self):
        work = self.make_tag(name="work")
        matching = self.make_note(title="Matches")
        self.tag_note(matching, work)
        self.make_note(title="No tag")

        result = get_filtered_notes(self.user, "work")

        assert list(result) == [matching]

    def test_requires_all_tags_in_a_plus_separated_filter(self):
        work = self.make_tag(name="work")
        urgent = self.make_tag(name="urgent")
        both = self.make_note(title="Both")
        self.tag_note(both, work)
        self.tag_note(both, urgent)
        only_work = self.make_note(title="Only work")
        self.tag_note(only_work, work)

        result = get_filtered_notes(self.user, "work+urgent")

        assert list(result) == [both]

    def test_extra_tags_beyond_the_filter_do_not_exclude_a_note(self):
        work = self.make_tag(name="work")
        extra = self.make_tag(name="extra")
        note = self.make_note(title="Has extra tag too")
        self.tag_note(note, work)
        self.tag_note(note, extra)

        result = get_filtered_notes(self.user, "work")

        assert list(result) == [note]

    def test_excludes_completed_notes(self):
        work = self.make_tag(name="work")
        note = self.make_note(title="Done", status="completed")
        self.tag_note(note, work)

        result = get_filtered_notes(self.user, "work")

        assert list(result) == []

    def test_only_returns_the_given_users_notes(self):
        work = self.make_tag(user=self.other_user, name="work")
        other_note = self.make_note(user=self.other_user, title="Not mine")
        self.tag_note(other_note, work)

        result = get_filtered_notes(self.user, "work")

        assert list(result) == []


class SendTemplatedMailTests(NotesTestCase):
    def test_sends_a_multipart_email_to_the_admins_by_default(self):
        send_templated_mail(
            subject="Test subject",
            template_name="link_check_report",
            context={"error_list": [], "redirect_list": []},
        )

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.subject == "Test subject"
        assert sent.to == [email for _name, email in settings.ADMINS]
        assert len(sent.alternatives) == 1
        html_body, mimetype = sent.alternatives[0]
        assert mimetype == "text/html"

    def test_renders_context_into_both_text_and_html_bodies(self):
        note = self.make_note(title="Broken bookmark", url="https://example.com/broken")

        send_templated_mail(
            subject="Test subject",
            template_name="link_check_report",
            context={"error_list": [note], "redirect_list": []},
        )

        sent = mail.outbox[0]
        assert "Broken bookmark" in sent.body
        html_body, _mimetype = sent.alternatives[0]
        assert "Broken bookmark" in html_body

    def test_returns_false_and_sends_nothing_when_there_are_no_recipients(self):
        with override_settings(ADMINS=[]):
            result = send_templated_mail(
                subject="Test subject",
                template_name="link_check_report",
                context={"error_list": [], "redirect_list": []},
            )

        assert result is False
        assert len(mail.outbox) == 0

    def test_recipient_list_overrides_the_admins_default(self):
        send_templated_mail(
            subject="Test subject",
            template_name="link_check_report",
            context={"error_list": [], "redirect_list": []},
            recipient_list=["someone@example.com"],
        )

        assert mail.outbox[0].to == ["someone@example.com"]
