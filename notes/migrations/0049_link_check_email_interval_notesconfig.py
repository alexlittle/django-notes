from django.db import migrations


def add_notes_config_entry(apps, schema_editor):
    NotesConfig = apps.get_model("notes", "NotesConfig")
    NotesConfig.objects.create(name="link_check.email_interval_hours", value="24")


def remove_notes_config_entry(apps, schema_editor):
    NotesConfig = apps.get_model("notes", "NotesConfig")
    NotesConfig.objects.filter(name="link_check.email_interval_hours").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0048_note_link_check_fail_count"),
    ]

    operations = [
        migrations.RunPython(add_notes_config_entry, remove_notes_config_entry),
    ]
