"""
Management command to replace one tag with one or more replacement tags
across all Notes, on a per-user basis.

Save this file as: <your_app>/management/commands/merge_tags.py
(create the `management/` and `management/commands/` folders with empty
__init__.py files if they don't already exist)

Update the import below to point at your actual app.

USAGE

  Split a single tag into two:
    python manage.py merge_tags --from books-to-read --to books,to-read

  Merge two tags into one:
    python manage.py merge_tags --from books --to books-to-read
    python manage.py merge_tags --from to-read --to books-to-read

  Preview changes without writing anything:
    python manage.py merge_tags --from books-to-read --to books,to-read --dry-run

  Also delete the old tag once nothing references it any more:
    python manage.py merge_tags --from books-to-read --to books,to-read --delete-old

NOTES

  - Tag.name is matched exactly (case-sensitive). Run with --dry-run first
    if you're not sure how many tags/notes will be affected.
  - Because Tag has a `user` FK, "books-to-read" might exist as several
    separate Tag rows (one per user). The command loops over each of them
    and creates/reuses the replacement tag(s) for that same user.
  - Existing (note, tag) links are never duplicated.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from notes.models import Note, NoteTag, Tag


class Command(BaseCommand):
    help = "Replace an old tag with one or more new tags across all notes, per-user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            dest="old_tag",
            required=True,
            help="Exact name of the tag to replace, e.g. books-to-read",
        )
        parser.add_argument(
            "--to",
            dest="new_tags",
            required=True,
            help="Comma-separated list of replacement tag names, e.g. books,to-read",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without changing anything",
        )
        parser.add_argument(
            "--delete-old",
            action="store_true",
            help="Delete the old tag afterwards if no notes reference it any more",
        )

    def handle(self, *args, **options):
        old_tag_name = options["old_tag"]
        new_tag_names = [t.strip() for t in options["new_tags"].split(",") if t.strip()]
        dry_run = options["dry_run"]
        delete_old = options["delete_old"]

        if not new_tag_names:
            raise CommandError("--to must contain at least one tag name")

        old_tags = Tag.objects.filter(name=old_tag_name)
        if not old_tags.exists():
            self.stdout.write(self.style.WARNING(f'No tags found with name "{old_tag_name}"'))
            return

        total_notes_updated = 0

        with transaction.atomic():
            for old_tag in old_tags:
                user = old_tag.user
                notes = Note.objects.filter(tags=old_tag)
                count = notes.count()
                self.stdout.write(f'User {user}: tag "{old_tag_name}" found on {count} note(s)')

                if count == 0:
                    continue

                # get or create each replacement tag for this same user
                new_tags = []
                for name in new_tag_names:
                    tag_obj, created = Tag.objects.get_or_create(user=user, name=name)
                    new_tags.append(tag_obj)
                    if created:
                        self.stdout.write(f'  Created new tag "{name}" for user {user}')

                for note in notes:
                    for new_tag in new_tags:
                        already_linked = NoteTag.objects.filter(note=note, tag=new_tag).exists()
                        if not already_linked:
                            if not dry_run:
                                NoteTag.objects.create(note=note, tag=new_tag)
                            self.stdout.write(
                                f'  Note {note.id} "{note.title}": + "{new_tag.name}"'
                            )
                        else:
                            self.stdout.write(
                                f'  Note {note.id} "{note.title}": already has "{new_tag.name}"'
                            )

                    if not dry_run:
                        NoteTag.objects.filter(note=note, tag=old_tag).delete()
                    self.stdout.write(f'  Note {note.id} "{note.title}": - "{old_tag_name}"')

                total_notes_updated += count

                if delete_old:
                    remaining = NoteTag.objects.filter(tag=old_tag).count()
                    if remaining == 0:
                        self.stdout.write(
                            f'  Deleting now-unused tag "{old_tag_name}" for user {user}'
                        )
                        if not dry_run:
                            old_tag.delete()
                    else:
                        self.stdout.write(
                            f'  Skipping delete: "{old_tag_name}" still used {remaining} time(s) for user {user}'
                        )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING("Dry run: rolling back, no changes were saved")
                )
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"Done. {total_notes_updated} note(s) processed."))
