import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def update_users(apps, schema_editor):
    notes_model = apps.get_model("notes", "Note")
    user_model = apps.get_model("auth", "user")

    notes = notes_model.objects.all()
    if not notes.exists():
        return

    try:
        user = user_model.objects.get(pk=1)
    except user_model.DoesNotExist:
        logger.warning("No user with pk=1 found; skipping note backfill.")
        return

    count = 0
    for obj in notes:
        obj.user = user
        try:
            obj.save()
            count += 1
        except Exception as e:
            logger.error(f"Error saving note {obj.pk}: {e}")
    logger.info(f"Updated {count} notes.")


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0014_note_type_backfill"),
    ]
    operations = [
        migrations.RunPython(update_users),
    ]
