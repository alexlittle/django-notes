from unittest.mock import patch

from django.urls import reverse

from tests.base import NotesTestCase


class SearchViewTests(NotesTestCase):
    def test_empty_query_returns_no_results(self):
        resp = self.client.get(reverse("notes:search"))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context["notes"]), [])
        self.assertEqual(resp.context["total_results"], 0)

    def test_results_come_from_combined_search_ids(self):
        match = self.make_note(title="Matches")
        self.make_note(title="Does not match")

        with patch(
            "notes.views.CombinedSearch.objects.combined_search",
            return_value=[{"id": match.pk}],
        ) as mocked:
            resp = self.client.get(reverse("notes:search"), {"q": "matches"})

        mocked.assert_called_with(self.user.id, "matches")
        self.assertEqual(list(resp.context["notes"]), [match])
        self.assertEqual(resp.context["total_results"], 1)

    def test_context_includes_prefilled_search_form_and_query(self):
        with patch("notes.views.CombinedSearch.objects.combined_search", return_value=[]):
            resp = self.client.get(reverse("notes:search"), {"q": "hello"})

        self.assertEqual(resp.context["query"], "hello")
        self.assertEqual(resp.context["form"].initial["q"], "hello")

    def test_search_relies_entirely_on_combined_search_for_user_scoping(self):
        # SearchView.get_queryset() does Note.objects.filter(pk__in=search_ids)
        # with no user= check of its own - see README for why this is safe
        # today but worth knowing about.
        other_users_note = self.make_note(user=self.other_user, title="Someone else's")

        with patch(
            "notes.views.CombinedSearch.objects.combined_search",
            return_value=[{"id": other_users_note.pk}],
        ):
            resp = self.client.get(reverse("notes:search"), {"q": "anything"})

        self.assertEqual(list(resp.context["notes"]), [other_users_note])


class TagAutocompleteViewTests(NotesTestCase):
    def test_requires_login(self):
        self.client.logout()

        resp = self.client.get(reverse("notes:tag-autocomplete"), {"term": "wo"})

        self.assertEqual(resp.status_code, 302)

    def test_returns_matching_tag_names_case_insensitively(self):
        self.make_tag(name="Work")
        self.make_tag(name="Workshop")
        self.make_tag(name="Personal")

        resp = self.client.get(reverse("notes:tag-autocomplete"), {"term": "wor"})

        self.assertEqual(resp.status_code, 200)
        self.assertCountEqual(resp.json(), ["Work", "Workshop"])

    def test_only_current_users_tags_are_suggested(self):
        self.make_tag(user=self.other_user, name="Workshop")
        mine = self.make_tag(name="Workshop")

        resp = self.client.get(reverse("notes:tag-autocomplete"), {"term": "work"})

        self.assertEqual(resp.json(), [mine.name])

    def test_results_are_capped_at_ten(self):
        for i in range(15):
            self.make_tag(name=f"tag{i}")

        resp = self.client.get(reverse("notes:tag-autocomplete"), {"term": "tag"})

        self.assertEqual(len(resp.json()), 10)
