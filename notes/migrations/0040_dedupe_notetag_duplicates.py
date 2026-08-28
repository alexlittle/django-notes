from django.db import migrations
from django.db.models import Count


def dedupe_notetags(apps, schema_editor):
    """Keep the oldest NoteTag row for each (note, tag) pair, delete the rest.

    Needed before the next migration adds a unique constraint on
    (note, tag) - without this, applying it against a database that
    already has duplicates would fail.
    """
    NoteTag = apps.get_model("notes", "NoteTag")
    duplicates = (
        NoteTag.objects.values("note_id", "tag_id").annotate(count=Count("id")).filter(count__gt=1)
    )
    for dup in duplicates:
        ids = list(
            NoteTag.objects.filter(note_id=dup["note_id"], tag_id=dup["tag_id"])
            .order_by("id")
            .values_list("id", flat=True)
        )
        NoteTag.objects.filter(id__in=ids[1:]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0039_alter_combinedsearch_options"),
    ]

    operations = [
        migrations.RunPython(dedupe_notetags, migrations.RunPython.noop),
    ]
