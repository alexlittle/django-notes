from django.core.management import call_command

from notes.models import Tag

from .base import NotesCommandTestCase


class CleanTagsCommandTests(NotesCommandTestCase):
    def test_deletes_tags_with_no_associated_notes_at_all(self):
        unused = self.make_tag(name="unused")

        call_command("clean_tags")

        self.assertFalse(Tag.objects.filter(pk=unused.pk).exists())

    def test_deletes_tags_whose_only_note_is_completed_archived_or_closed(self):
        # note_count now matches Tag.note_count() elsewhere in the app,
        # which excludes completed/archived/closed notes - so a tag whose
        # only note is e.g. archived counts as "unused" here too.
        tag = self.make_tag(name="unused")
        archived_note = self.make_note(type="task", title="Old", status="archived")
        self.tag_note(archived_note, tag)

        call_command("clean_tags")

        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())

    def test_keeps_tags_that_have_at_least_one_active_note(self):
        tag = self.make_tag(name="used")
        open_note = self.make_note(type="task", title="Still open", status="open")
        self.tag_note(open_note, tag)

        call_command("clean_tags")

        self.assertTrue(Tag.objects.filter(pk=tag.pk).exists())

    def test_favourite_tags_are_never_deleted_even_if_unused(self):
        fav = self.make_tag(name="fav", favourite=True)

        call_command("clean_tags")

        self.assertTrue(Tag.objects.filter(pk=fav.pk).exists())

    def test_operates_across_all_users_not_just_one(self):
        # There's no user= filter in the command's queryset, so it cleans
        # unused tags for every user in one run - not scoped to any
        # particular account.
        mine = self.make_tag(user=self.user, name="unused-mine")
        theirs = self.make_tag(user=self.other_user, name="unused-theirs")

        call_command("clean_tags")

        self.assertFalse(Tag.objects.filter(pk=mine.pk).exists())
        self.assertFalse(Tag.objects.filter(pk=theirs.pk).exists())
