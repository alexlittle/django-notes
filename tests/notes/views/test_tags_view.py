from django.urls import reverse

from tests.base import NotesTestCase


class TagsViewTests(NotesTestCase):
    def test_only_current_users_tags_shown(self):
        mine = self.make_tag(name="mine")
        self.make_tag(user=self.other_user, name="not-mine")

        resp = self.client.get(reverse("notes:tags"))

        self.assertEqual(list(resp.context["tags"]), [mine])

    def test_default_ordering_is_favourite_then_name(self):
        fav = self.make_tag(name="zzz-fav", favourite=True)
        non_fav_a = self.make_tag(name="alpha", favourite=False)
        non_fav_b = self.make_tag(name="beta", favourite=False)

        resp = self.client.get(reverse("notes:tags"))

        self.assertEqual(list(resp.context["tags"]), [fav, non_fav_a, non_fav_b])

    def test_custom_orderby_param_is_respected(self):
        b_tag = self.make_tag(name="beta")
        a_tag = self.make_tag(name="alpha")

        resp = self.client.get(reverse("notes:tags"), {"orderby": "name"})

        self.assertEqual(list(resp.context["tags"]), [a_tag, b_tag])

    def test_note_count_annotation(self):
        tag = self.make_tag(name="counted")
        for i in range(2):
            note = self.make_note(title=f"Note {i}")
            self.tag_note(note, tag)

        resp = self.client.get(reverse("notes:tags"))

        # TagsView paginates (paginate_by=50), so resp.context["tags"] is
        # already a sliced page of results - calling .get() on it again
        # raises "Cannot filter a query once a slice has been taken."
        # Look it up in the returned page instead of re-querying.
        found = next(t for t in resp.context["tags"] if t.pk == tag.pk)
        self.assertEqual(found.count, 2)
