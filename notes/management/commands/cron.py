from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from notes.models import Tag


class Command(BaseCommand):
    help = _(u"Cron task")
    errors = []

    def handle(self, *args, **options):

        # delete unused tags
        call_command('clean_tags')

        # delete tasks completed over a month ago
