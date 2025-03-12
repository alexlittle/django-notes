from django.db import migrations
import logging

logger = logging.getLogger(__name__)

def update_tasks(apps, schema_editor):
    model = apps.get_model('notes', 'Note')
    notes = model.objects.filter(url='')
    for obj in notes:
        obj.type = 'task'
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0013_note_type'),
    ]

    operations = [
        migrations.RunPython(update_tasks),
    ]