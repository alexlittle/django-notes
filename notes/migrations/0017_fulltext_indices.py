from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0016_alter_note_estimated_effort'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE notes_note ADD FULLTEXT INDEX note_fulltext_index (title, url, description, status, priority);",
            "ALTER TABLE notes_note  DROP INDEX note_fulltext_index;",
        ),
        migrations.RunSQL(
            "ALTER TABLE notes_tag ADD FULLTEXT INDEX tag_fulltext_index (name, slug);",
            "ALTER TABLE notes_tag  DROP INDEX tag_fulltext_index;",
        ),
    ]