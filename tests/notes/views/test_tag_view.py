from unittest.mock import patch

from django.urls import reverse

from notes.models import Note
from tests.base import NotesTestCase


class TagViewTests(NotesTestCase):
    def test_uses_get_filtered_notes_and_orders_by_get_param(self):
        note_a = self.make_note(title="A")
        note_b = self.make_note(title="B")
        fake_queryset = Note.objects.filter(pk__in=[note_a.pk, note_b.pk])

        with (
            patch("notes.views.get_filtered_notes", return_value=fake_queryset) as mocked,
            patch("notes.views.suggest_tags", return_value=[]),
        ):
            resp = self.client.get(
                reverse("notes:tag_view", kwargs={"tag_slug": "work"}), {"order": "title"}
            )

        mocked.assert_called_with(self.user, "work")
        self.assertEqual(list(resp.context["notes"]), [note_a, note_b])

    def test_default_ordering_param_is_due_date_descending(self):
        with (
            patch("notes.views.get_filtered_notes", return_value=Note.objects.none()),
            patch("notes.views.suggest_tags", return_value=[]),
        ):
            resp = self.client.get(reverse("notes:tag_view", kwargs={"tag_slug": "work"}))

        self.assertEqual(resp.status_code, 200)

    def test_context_includes_matching_tags_and_related_tag_suggestions(self):
        work = self.make_tag(name="work")
        urgent = self.make_tag(name="urgent")
        self.make_tag(user=self.other_user, name="also-work")

        with (
            patch("notes.views.get_filtered_notes", return_value=Note.objects.none()),
            patch("notes.views.suggest_tags", return_value=["related-tag"]) as mocked_suggest,
        ):
            resp = self.client.get(
                reverse("notes:tag_view", kwargs={"tag_slug": f"{work.slug}+{urgent.slug}"})
            )

        self.assertCountEqual(resp.context["tags"], [work, urgent])
        self.assertEqual(resp.context["related_tags"], ["related-tag"])
        mocked_suggest.assert_called_with([work.slug, urgent.slug])
