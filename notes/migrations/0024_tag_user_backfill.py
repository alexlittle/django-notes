from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def update_tags(apps, schema_editor):
    notes_model = apps.get_model('notes', 'Tag')
    user_model = apps.get_model('auth', 'user')
    user = user_model.objects.get(pk=1)
    tags = notes_model.objects.all()
    count = 0
    for obj in tags:
        obj.user = user
        try:
            obj.save()
            count += 1
        except Exception as e:
            logger.error(f"Error saving tag {obj.pk}: {e}")
    logger.info(f"Updated {count} tags.")


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0023_tag_user'),
    ]

    operations = [
        migrations.RunPython(update_tags),
    ]