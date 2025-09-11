import pandas as pd
import itertools
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from collections import defaultdict

from notes.models import Note, Tag

class Command(BaseCommand):
    help = _(u"Tags Matrix")
    errors = []

    def handle(self, *args, **options):

        notes = Note.fetch_bookmark_tags()

        co_occurrence = defaultdict(int)

        for tags in notes.values():
            for a, b, c in itertools.combinations(sorted(tags), 3):
                co_occurrence[(a, b, c)] += 1

        df = pd.DataFrame(
            [(a, b, c, count) for (a, b, c), count in co_occurrence.items()],
            columns=["tag1", "tag2", "tag3", "count"]
        )

        print(df.sort_values("count", ascending=False).head(50))

