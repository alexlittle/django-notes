"""Tests for notes.templatetags.custom_filters.

No database access is required - the filter only reads .due_date off
whatever objects it's handed, so plain stand-ins are enough.
"""

from dataclasses import dataclass
from datetime import date

from django.template import Context, Template

from notes.templatetags.custom_filters import get_previous_due_date, register


@dataclass
class FakeNote:
    due_date: date | None


def render(notes, current_index):
    template = Template("{% load custom_filters %}{{ notes|get_previous_due_date:current_index }}")
    return template.render(Context({"notes": notes, "current_index": current_index}))


class TestRegistration:
    def test_filter_is_registered(self):
        assert "get_previous_due_date" in register.filters

    def test_registered_callable_is_the_filter(self):
        assert register.filters["get_previous_due_date"] is get_previous_due_date


class TestGetPreviousDueDate:
    def test_first_item_has_no_previous_due_date(self):
        notes = [FakeNote(due_date=date(2026, 1, 1))]

        assert get_previous_due_date(notes, 0) is None

    def test_negative_index_also_has_no_previous_due_date(self):
        notes = [FakeNote(due_date=date(2026, 1, 1))]

        assert get_previous_due_date(notes, -1) is None

    def test_later_item_returns_the_previous_items_due_date(self):
        notes = [FakeNote(due_date=date(2026, 1, 1)), FakeNote(due_date=date(2026, 2, 1))]

        assert get_previous_due_date(notes, 1) == date(2026, 1, 1)

    def test_previous_items_due_date_can_itself_be_none(self):
        notes = [FakeNote(due_date=None), FakeNote(due_date=date(2026, 2, 1))]

        assert get_previous_due_date(notes, 1) is None

    def test_renders_as_empty_string_for_the_first_item_in_a_template(self):
        notes = [FakeNote(due_date=date(2026, 1, 1))]

        assert render(notes, 0) == "None"
