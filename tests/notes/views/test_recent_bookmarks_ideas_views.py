from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from tests.base import NotesTestCase


class RecentViewTests(NotesTestCase):
    def test_only_current_users_notes_shown_across_all_types(self):
        mine_task = self.make_note(type="task", title="Task")
        mine_bookmark = self.make_note(type="bookmark", title="Bookmark")
        mine_idea = self.make_note(type="idea", title="Idea")
        self.make_note(user=self.other_user, type="task", title="Not mine")

        with patch("notes.views.is_showall", return_value=False):
            resp = self.client.get(reverse("notes:recent"))

        self.assertEqual(resp.status_code, 200)
        self.assertCountEqual(resp.context["tasks"], [mine_task, mine_bookmark, mine_idea])

    def test_ordered_by_most_recently_updated_first(self):
        older = self.make_note(title="Older")
        newer = self.make_note(title="Newer")
        newer.update_date = timezone.now() + timedelta(hours=1)
        newer.save()

        with patch("notes.views.is_showall", return_value=False):
            resp = self.client.get(reverse("notes:recent"))

        notes = list(resp.context["tasks"])
        self.assertLess(notes.index(newer), notes.index(older))

    def test_context_includes_showall_flag(self):
        with patch("notes.views.is_showall", return_value=True):
            resp = self.client.get(reverse("notes:recent"))

        self.assertTrue(resp.context["showall"])


class BookmarksViewTests(NotesTestCase):
    def test_only_bookmark_type_notes_for_current_user(self):
        bookmark = self.make_note(type="bookmark", title="Bookmark")
        self.make_note(type="task", title="Task")
        self.make_note(user=self.other_user, type="bookmark", title="Not mine")

        resp = self.client.get(reverse("notes:bookmarks"))

        self.assertEqual(list(resp.context["notes"]), [bookmark])

    def test_link_check_result_controls_which_status_icon_is_shown(self):
        self.make_note(
            type="bookmark", title="OK", url="https://ok.example.com", link_check_result="ok"
        )
        self.make_note(
            type="bookmark",
            title="Redirected",
            url="https://redirected.example.com",
            link_check_result="redirect",
        )
        self.make_note(
            type="bookmark",
            title="Broken",
            url="https://broken.example.com",
            link_check_result="error",
        )

        resp = self.client.get(reverse("notes:bookmarks"))
        content = resp.content.decode()

        self.assertIn("icon-yes.svg", content)
        self.assertIn("icon-alert.svg", content)
        self.assertIn("icon-no.svg", content)


class IdeasViewTests(NotesTestCase):
    def test_only_idea_type_notes_for_current_user(self):
        idea = self.make_note(type="idea", title="Idea")
        self.make_note(type="task", title="Task")
        self.make_note(user=self.other_user, type="idea", title="Not mine")

        resp = self.client.get(reverse("notes:ideas"))

        self.assertEqual(list(resp.context["notes"]), [idea])
