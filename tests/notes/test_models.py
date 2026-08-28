"""Tests for the uncovered corners of notes.models."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from notes.models import CombinedSearch, Note, NoteTag, Tag, TagSuggestion, TagSuggestionInputTag
from tests.base import NotesTestCase

User = get_user_model()


class NoteStrTests(NotesTestCase):
    def test_str_returns_the_title_when_present(self):
        note = Note(title="A title", url="http://example.com")

        assert str(note) == "A title"

    def test_str_falls_back_to_the_url_when_title_is_blank(self):
        note = Note(title="", url="http://example.com/bookmark")

        assert str(note) == "http://example.com/bookmark"


class GetNextDueDateTests(NotesTestCase):
    """Direct, in-memory tests of Note.get_next_due_date - no save() needed."""

    due_date = date(2026, 1, 31)

    def test_no_recurrence_value_returns_none(self):
        note = Note(due_date=self.due_date, recurrence="none")

        assert note.get_next_due_date() is None

    def test_blank_recurrence_returns_none(self):
        note = Note(due_date=self.due_date, recurrence="")

        assert note.get_next_due_date() is None

    def test_null_recurrence_returns_none(self):
        note = Note(due_date=self.due_date, recurrence=None)

        assert note.get_next_due_date() is None

    def test_daily_adds_one_day(self):
        note = Note(due_date=self.due_date, recurrence="daily")

        assert note.get_next_due_date() == self.due_date + timedelta(days=1)

    def test_weekly_adds_one_week(self):
        note = Note(due_date=self.due_date, recurrence="weekly")

        assert note.get_next_due_date() == self.due_date + timedelta(weeks=1)

    def test_biweekly_adds_two_weeks(self):
        note = Note(due_date=self.due_date, recurrence="biweekly")

        assert note.get_next_due_date() == self.due_date + timedelta(weeks=2)

    def test_monthly_adds_one_calendar_month(self):
        note = Note(due_date=self.due_date, recurrence="monthly")

        assert note.get_next_due_date() == date(2026, 2, 28)

    def test_quarterly_adds_three_calendar_months(self):
        note = Note(due_date=self.due_date, recurrence="quarterly")

        assert note.get_next_due_date() == date(2026, 4, 30)

    def test_annually_adds_one_calendar_year(self):
        note = Note(due_date=self.due_date, recurrence="annually")

        assert note.get_next_due_date() == date(2027, 1, 31)

    def test_unrecognised_recurrence_falls_back_to_the_existing_due_date(self):
        # None of the RECURRENCE_OPTIONS choices reach this branch - it only
        # fires for a value outside the declared choices (choices aren't
        # enforced at the DB/ORM level, so this can happen in practice).
        note = Note(due_date=self.due_date, recurrence="bogus")

        assert note.get_next_due_date() == self.due_date


class HasImportantTagTests(NotesTestCase):
    def test_high_priority_is_important_without_checking_tags(self):
        note = Note(priority="high")

        assert note.has_important_tag() is True

    def test_non_high_priority_without_a_matching_tag_is_not_important(self):
        note = self.make_note(priority="low")

        assert note.has_important_tag() is False


class TagSuggestionStrTests(NotesTestCase):
    def test_tag_suggestion_str_includes_an_arrow(self):
        suggestion = TagSuggestion(suggested_tag="reading", confidence=0.5, lift=1.0, support=0.5)

        assert str(suggestion) == "→ reading"

    def test_tag_suggestion_input_tag_str_is_just_the_tag(self):
        suggestion = TagSuggestion.objects.create(
            suggested_tag="reading", confidence=0.5, lift=1.0, support=0.5
        )
        input_tag = TagSuggestionInputTag(suggestion=suggestion, tag="books")

        assert str(input_tag) == "books"


class CombinedSearchTests(TransactionTestCase):
    """Exercises the raw MySQL fulltext query in CombinedSearchManager.

    Uses TransactionTestCase rather than NotesTestCase/TestCase: InnoDB
    FULLTEXT search only sees committed data, and TestCase wraps each test
    in a transaction that's rolled back rather than committed, so a note
    inserted during the test would never be visible to the MATCH AGAINST
    query.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="alex", password="pw12345!")
        self.other_user = User.objects.create_user(username="jamie", password="pw12345!")

    def make_note(self, user=None, type="task", title="A note", **kwargs):  # noqa: A002
        return Note.objects.create(user=user or self.user, type=type, title=title, **kwargs)

    def make_tag(self, user=None, name="tag1", **kwargs):
        return Tag.objects.create(user=user or self.user, name=name, **kwargs)

    def tag_note(self, note, tag):
        NoteTag.objects.get_or_create(note=note, tag=tag)

    def test_matches_a_note_field_and_scopes_to_the_requesting_user(self):
        # The query INNER JOINs through notes_notetag/notes_tag, so a note
        # with zero tags can never appear in a result - even on a pure
        # title match. Every note here needs at least one tag just to be
        # eligible, regardless of what it matches on.
        #
        # NATURAL LANGUAGE MODE also treats a word present in over half of
        # a table's rows as too common to be meaningful and scores it
        # zero, so "gadgetsphere" is kept to a minority of notes_note too.
        tag = self.make_tag(name="misc")
        mine = self.make_note(title="Gadgetsphere review")
        self.tag_note(mine, tag)
        theirs = self.make_note(user=self.other_user, title="Gadgetsphere comparison")
        self.tag_note(theirs, self.make_tag(user=self.other_user, name="misc"))
        for i in range(5):
            noise = self.make_note(title=f"Something unrelated {i}")
            self.tag_note(noise, tag)

        results = CombinedSearch.objects.combined_search(self.user.id, "gadgetsphere")

        assert [r["id"] for r in results] == [mine.pk]

    def test_a_note_with_no_tags_is_never_returned_even_on_a_field_match(self):
        untagged = self.make_note(title="Gadgetsphere review")

        results = CombinedSearch.objects.combined_search(self.user.id, "gadgetsphere")

        assert [r["id"] for r in results] == []
        assert untagged.tags.count() == 0

    def test_matches_via_a_notes_tag_name(self):
        note = self.make_note(title="Untitled", type="bookmark")
        tag = self.make_tag(name="astrophysics")
        self.tag_note(note, tag)

        results = CombinedSearch.objects.combined_search(self.user.id, "astrophysics")

        assert [r["id"] for r in results] == [note.pk]

    def test_no_match_returns_an_empty_list(self):
        note = self.make_note(title="Gadgetsphere review")
        self.tag_note(note, self.make_tag(name="misc"))

        results = CombinedSearch.objects.combined_search(self.user.id, "nonexistentword")

        assert results == []
