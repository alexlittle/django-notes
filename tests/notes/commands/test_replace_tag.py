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

    def test_can_create_a_duplicate_notetag_row_if_note_already_has_both_tags(self):
        # nt.tag = newtag; nt.save() re-points the *existing* NoteTag row -
        # it doesn't check whether the note already has a separate NoteTag
        # row for new_tag. NoteTag has no unique_together on (note, tag),
        # so this scenario leaves two NoteTag rows both pointing at
        # (note, new_tag).
        old_tag = self.make_tag(name="old")
        new_tag = self.make_tag(name="new")
        note = self.make_note(title="Has both already")
        self.tag_note(note, old_tag)
        self.tag_note(note, new_tag)

        call_command("replace_tag", old_tag.slug, new_tag.slug)

        self.assertEqual(NoteTag.objects.filter(note=note, tag=new_tag).count(), 2)
