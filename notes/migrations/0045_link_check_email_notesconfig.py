from django.db import migrations


def add_notes_config_entries(apps, schema_editor):
    NotesConfig = apps.get_model("notes", "NotesConfig")
    NotesConfig.objects.create(name="link_check.email_enabled", value="false")
    NotesConfig.objects.create(name="link_check.email_recipients", value="")


def remove_notes_config_entries(apps, schema_editor):
    NotesConfig = apps.get_model("notes", "NotesConfig")
    NotesConfig.objects.filter(
        name__in=["link_check.email_enabled", "link_check.email_recipients"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0044_alter_note_link_check_result"),
    ]

    operations = [
        migrations.RunPython(add_notes_config_entries, remove_notes_config_entries),
    ]
