
from django.db import migrations

def add_notes_config_entries(apps, schema_editor):
    NotesConfig = apps.get_model('notes', 'NotesConfig')
    NotesConfig.objects.create(name='schedule.important.tags', value='assessment')

class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0035_prefill_notesconfig'),
    ]

    operations = [
        migrations.RunPython(add_notes_config_entries),
    ]
