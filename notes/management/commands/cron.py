from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from datetime import datetime
from datetime import timedelta

from notes.models import Note

class Command(BaseCommand):
    help = _(u"Cron task")
    errors = []

    def handle(self, *args, **options):

        # delete unused tags
        call_command('clean_tags')

        # delete tasks completed over a month ago
        delete_date = datetime.now().date() - timedelta(days=31)
        old_tasks = Note.objects.filter(due_date__isnull=False,
                                        type="task",
                                        status='completed',
                                        completed_date__lte=delete_date)
        for ot in old_tasks:
            ot.delete()