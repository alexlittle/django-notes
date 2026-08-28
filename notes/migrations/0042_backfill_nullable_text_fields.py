from django.db import migrations


def backfill_nulls(apps, schema_editor):
    """Replace NULL with the field's intended default before the next
    migration makes these columns NOT NULL - required on MySQL, which
    rejects an ALTER TABLE ... NOT NULL against a column that still has
    NULL rows.
    """
    NotesProfile = apps.get_model("notes", "NotesProfile")
    Tag = apps.get_model("notes", "Tag")
    Note = apps.get_model("notes", "Note")

    NotesProfile.objects.filter(timezone__isnull=True).update(timezone="UTC")
    Tag.objects.filter(label__isnull=True).update(label="")
    Note.objects.filter(url__isnull=True).update(url="")
    Note.objects.filter(description__isnull=True).update(description="")
    Note.objects.filter(priority__isnull=True).update(priority="")
    Note.objects.filter(recurrence__isnull=True).update(recurrence="")


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0041_notetag_unique_note_tag"),
    ]

    operations = [
        migrations.RunPython(backfill_nulls, migrations.RunPython.noop),
    ]
