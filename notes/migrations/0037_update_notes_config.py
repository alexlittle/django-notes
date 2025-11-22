
from django.db import migrations

def update_config_entries(apps, schema_editor):
    NotesConfig = apps.get_model('notes', 'NotesConfig')
    NotesConfig.objects.get(name='schedule.start.date').delete()
    NotesConfig.objects.get(name='schedule.end.date').delete()
    NotesConfig.objects.create(name='schedule.start.days', value='14')
    NotesConfig.objects.create(name='schedule.end.days', value='21')

class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0036_important_notesconfig'),
    ]

    operations = [
        migrations.RunPython(update_config_entries),
    ]
