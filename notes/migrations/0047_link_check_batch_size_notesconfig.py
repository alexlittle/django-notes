from django.db import migrations


def add_notes_config_entry(apps, schema_editor):
    NotesConfig = apps.get_model("notes", "NotesConfig")
    NotesConfig.objects.create(name="link_check.batch_size", value="50")


def remove_notes_config_entry(apps, schema_editor):
    NotesConfig = apps.get_model("notes", "NotesConfig")
    NotesConfig.objects.filter(name="link_check.batch_size").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0046_note_link_check_ignore_redirects"),
    ]

    operations = [
        migrations.RunPython(add_notes_config_entry, remove_notes_config_entry),
    ]
