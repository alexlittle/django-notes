import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def update_tags(apps, schema_editor):
    tag_model = apps.get_model("notes", "Tag")
    user_model = apps.get_model("auth", "user")

    tags = tag_model.objects.all()
    if not tags.exists():
        return

    try:
        user = user_model.objects.get(pk=1)
    except user_model.DoesNotExist:
        logger.warning("No user with pk=1 found; skipping tag backfill.")
        return

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
        ("notes", "0023_tag_user"),
    ]
    operations = [
        migrations.RunPython(update_tags),
    ]
