from django.core.management import call_command

from notes.models import NoteTag, Tag

from .base import NotesCommandTestCase


class ReplaceTagCommandTests(NotesCommandTestCase):
    def test_reassigns_all_notes_from_old_tag_to_new_tag(self):
        old_tag = self.make_tag(name="old")
        new_tag = self.make_tag(name="new")
        note_a = self.make_note(title="A")
        note_b = self.make_note(title="B")
        self.tag_note(note_a, old_tag)
        self.tag_note(note_b, old_tag)

        call_command("replace_tag", old_tag.slug, new_tag.slug)

        self.assertTrue(NoteTag.objects.filter(note=note_a, tag=new_tag).exists())
        self.assertTrue(NoteTag.objects.filter(note=note_b, tag=new_tag).exists())
        self.assertFalse(Tag.objects.filter(pk=old_tag.pk).exists())

    def test_raises_for_an_unknown_slug(self):
        new_tag = self.make_tag(name="new")

        with self.assertRaises(Tag.DoesNotExist):
            call_command("replace_tag", "does-not-exist", new_tag.slug)

    def test_a_note_with_both_tags_already_ends_up_with_one_notetag_row(self):
        # NoteTag now has a unique constraint on (note, tag), so re-pointing
        # the old row to new_tag would raise an IntegrityError if the note
        # already has a separate NoteTag row for new_tag. The command
        # drops the old row instead of re-pointing it in that case.
        old_tag = self.make_tag(name="old")
        new_tag = self.make_tag(name="new")
        note = self.make_note(title="Has both already")
        self.tag_note(note, old_tag)
        self.tag_note(note, new_tag)

        call_command("replace_tag", old_tag.slug, new_tag.slug)

        self.assertEqual(NoteTag.objects.filter(note=note, tag=new_tag).count(), 1)
