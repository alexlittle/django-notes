from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from notes.models import Tag


class Command(BaseCommand):
    help = _(u"Check for tags that are very similar")
    errors = []

    def handle(self, *args, **options):
        pass