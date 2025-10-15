
from django.db import migrations

def add_notes_config_entries(apps, schema_editor):
    NotesConfig = apps.get_model('notes', 'NotesConfig')
    NotesConfig.objects.create(name='retain.days', value='120')
    NotesConfig.objects.create(name='schedule.start.date', value='2025-01-01')
    NotesConfig.objects.create(name='schedule.end.date', value='2025-12-31')
    NotesConfig.objects.create(name='schedule.study.tags', value='')

class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0034_tag_label'),
    ]

    operations = [
        migrations.RunPython(add_notes_config_entries),
    ]
