from unittest.mock import patch

from django.urls import reverse

from notes.models import SavedFilter
from tests.base import NotesTestCase


class FavouritesViewTests(NotesTestCase):
    def test_only_current_users_favourite_tags_shown(self):
        fav = self.make_tag(name="fav", favourite=True)
        self.make_tag(name="not-fav", favourite=False)
        self.make_tag(user=self.other_user, name="other-fav", favourite=True)

        resp = self.client.get(reverse("notes:favs"))

        self.assertEqual(list(resp.context["tags"]), [fav])

    def test_saved_filters_are_listed_with_their_counts(self):
        SavedFilter.objects.create(name="High priority", value="priority:high")

        with patch("notes.models.get_filtered_notes") as mocked:
            mocked.return_value.count.return_value = 4
            resp = self.client.get(reverse("notes:favs"))

        filters = dict((f.name, count) for f, count in resp.context["filters"])
        self.assertEqual(filters["High priority"], 4)
        mocked.assert_called_with(self.user, "priority:high")
