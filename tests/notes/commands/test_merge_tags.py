from django.core.management import CommandError, call_command

from notes.models import NoteTag, Tag

from .base import NotesCommandTestCase


class MergeTagsCommandTests(NotesCommandTestCase):
    def test_raises_when_to_argument_has_no_usable_tag_names(self):
        with self.assertRaises(CommandError):
            call_command("merge_tags", old_tag="whatever", new_tags="  , ,")

    def test_unknown_from_tag_is_a_no_op(self):
        note = self.make_note(title="Untouched")
        tag = self.make_tag(name="something-else")
        self.tag_note(note, tag)

        call_command("merge_tags", old_tag="does-not-exist", new_tags="anything")

        self.assertTrue(NoteTag.objects.filter(note=note, tag=tag).exists())

    def test_splits_one_tag_into_several_replacement_tags(self):
        old_tag = self.make_tag(name="books-to-read")
        note = self.make_note(title="A book")
        self.tag_note(note, old_tag)

        call_command("merge_tags", old_tag="books-to-read", new_tags="books,to-read")

        new_names = sorted(NoteTag.objects.filter(note=note).values_list("tag__name", flat=True))
        self.assertEqual(new_names, ["books", "to-read"])

    def test_merges_one_tag_into_an_existing_one(self):
        target = self.make_tag(name="books-to-read")
        source = self.make_tag(name="to-read")
        note = self.make_note(title="A book")
        self.tag_note(note, source)

        call_command("merge_tags", old_tag="to-read", new_tags="books-to-read")

        names = list(NoteTag.objects.filter(note=note).values_list("tag__name", flat=True))
        self.assertEqual(names, ["books-to-read"])
        self.assertEqual(NoteTag.objects.filter(note=note, tag=target).count(), 1)

    def test_reuses_an_existing_tag_of_the_same_name_instead_of_duplicating(self):
        old_tag = self.make_tag(name="to-read")
        self.make_tag(name="books-to-read")  # already exists for this user
        note = self.make_note(title="A book")
        self.tag_note(note, old_tag)

        call_command("merge_tags", old_tag="to-read", new_tags="books-to-read")

        self.assertEqual(Tag.objects.filter(user=self.user, name="books-to-read").count(), 1)

    def test_does_not_duplicate_a_link_the_note_already_has(self):
        old_tag = self.make_tag(name="to-read")
        new_tag = self.make_tag(name="books-to-read")
        note = self.make_note(title="Already has both")
        self.tag_note(note, old_tag)
        self.tag_note(note, new_tag)

        call_command("merge_tags", old_tag="to-read", new_tags="books-to-read")

        self.assertEqual(NoteTag.objects.filter(note=note, tag=new_tag).count(), 1)
        self.assertFalse(NoteTag.objects.filter(note=note, tag=old_tag).exists())

    def test_dry_run_leaves_the_database_completely_unchanged(self):
        old_tag = self.make_tag(name="to-read")
        note = self.make_note(title="A book")
        self.tag_note(note, old_tag)

        call_command("merge_tags", old_tag="to-read", new_tags="books-to-read", dry_run=True)

        # Nothing moved...
        self.assertTrue(NoteTag.objects.filter(note=note, tag=old_tag).exists())
        # ...and the new tag was never actually persisted either - the
        # get_or_create() for it runs unconditionally, but it's inside the
        # same atomic() block that gets rolled back for a dry run.
        self.assertFalse(Tag.objects.filter(user=self.user, name="books-to-read").exists())

    def test_delete_old_removes_the_tag_once_it_has_no_notes_left(self):
        old_tag = self.make_tag(name="to-read")
        note = self.make_note(title="A book")
        self.tag_note(note, old_tag)

        call_command("merge_tags", old_tag="to-read", new_tags="books-to-read", delete_old=True)

        self.assertFalse(Tag.objects.filter(pk=old_tag.pk).exists())

    def test_each_users_matching_tag_is_processed_independently(self):
        my_old = self.make_tag(user=self.user, name="books")
        their_old = self.make_tag(user=self.other_user, name="books")
        my_note = self.make_note(user=self.user, title="Mine")
        their_note = self.make_note(user=self.other_user, title="Theirs")
        self.tag_note(my_note, my_old)
        self.tag_note(their_note, their_old)

        call_command("merge_tags", old_tag="books", new_tags="reading", delete_old=True)

        my_new = Tag.objects.get(user=self.user, name="reading")
        their_new = Tag.objects.get(user=self.other_user, name="reading")
        self.assertTrue(NoteTag.objects.filter(note=my_note, tag=my_new).exists())
        self.assertTrue(NoteTag.objects.filter(note=their_note, tag=their_new).exists())
        self.assertFalse(Tag.objects.filter(pk=my_old.pk).exists())
        self.assertFalse(Tag.objects.filter(pk=their_old.pk).exists())
