
import dateutil.relativedelta

from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from notes.models import Note


class Command(BaseCommand):
    help = _(u"Looks for very old notes")

    def add_arguments(self, parser):
        parser.add_argument('start_years', type=int, default=0)
        parser.add_argument('no_years', type=int, default=0)

    def handle(self, *args, **options):
        start_years = options['start_years']
        no_years = options['no_years']
        start_cut_off_date = timezone.now() - dateutil.relativedelta.relativedelta(years=start_years)
        end_cut_off_date = start_cut_off_date - dateutil.relativedelta.relativedelta(years=no_years)
        old_notes = Note.objects.filter(create_date__lte=start_cut_off_date, create_date__gte=end_cut_off_date)
        for idx, ob in enumerate(old_notes):
            print()
            print("%d/%d %s - %s " % (idx, old_notes.count(), ob.title, ob.url))
            print("Added: %s" % ob.create_date)
            print("Edit: %s%s" % ("http://localhost:9030", reverse('admin:notes_note_change', args=[ob.id])))
            tags = ', '.join(ob.tags.all().values_list('name', flat=True))
            print("Tags: %s" % tags)
            print()
            accept = input(_(u"Delete this link? [y/n]"))
            if accept == 'y':
                ob.delete()
