from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from notes.models import Note, NotesConfig


class Command(BaseCommand):
    help = _("Cron task")
    errors = []

    def handle(self, *args, **options):

        # delete unused tags
        call_command("clean_tags")

        # rebuild tag suggestions
        call_command("build_tag_suggestions")

        try:
            days_to_keep = int(NotesConfig.get_value("retain.days"))
        except ValueError:
            days_to_keep = 31
        # delete tasks completed over a month ago
        delete_datetime = timezone.now() - timedelta(days=days_to_keep)
        old_completed_tasks = Note.objects.filter(
            type="task", status="completed", completed_date__lte=delete_datetime.date()
        )

        for ot in old_completed_tasks:
            print(f"{ot.title} deleted")
            ot.delete()

        old_closed_tasks = Note.objects.filter(
            type="task", status="closed", update_date__lte=delete_datetime
        )
        for ot in old_closed_tasks:
            print(f"{ot.title} deleted")
            ot.delete()

        old_archived_tasks = Note.objects.filter(
            type="task", status="archived", update_date__lte=delete_datetime
        )
        for ot in old_archived_tasks:
            print(f"{ot.title} deleted")
            ot.delete()

        try:
            link_check_days = int(NotesConfig.get_value("link_check.days"))
        except ValueError:
            link_check_days = 7
        # only re-checks links whose link_check_date is older than link_check_days,
        # so running this every hour still only touches each link roughly weekly
        call_command("link_checker", link_check_days, interactive=False)
