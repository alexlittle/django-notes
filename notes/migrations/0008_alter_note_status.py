# Generated by Django 5.1.7 on 2025-03-10 06:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0007_note_completed_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='note',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('inprogress', 'In progress'), ('completed', 'Completed'), ('closed', 'Closed'), ('archived', 'Archived')], default='open', max_length=15),
        ),
    ]
