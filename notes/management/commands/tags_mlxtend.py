import pandas as pd

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules

from notes.models import Note, Tag

class Command(BaseCommand):
    help = _(u"Tags Matrix")
    errors = []

    def handle(self, *args, **options):

        notes = Note.fetch_bookmark_tags()

        transactions = list(notes.values())

        te = TransactionEncoder()
        te_array = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_array, columns=te.columns_)

        frequent_itemsets = apriori(df, min_support=0.002, use_colnames=True)

        print(frequent_itemsets.sort_values("support", ascending=False))

        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.6)

        print(rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']])

