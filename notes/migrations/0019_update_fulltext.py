from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0018_combinedsearch_alter_notehistory_action'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE notes_note  DROP INDEX note_fulltext_index;",
            "ALTER TABLE notes_note  DROP INDEX note_fulltext_index;",
        ),
        migrations.RunSQL(
            "ALTER TABLE notes_note ADD FULLTEXT INDEX note_fulltext_index (type, title, url, description, status, priority);",
            "ALTER TABLE notes_note  DROP INDEX note_fulltext_index;",
        ),

    ]