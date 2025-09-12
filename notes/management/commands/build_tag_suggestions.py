from django.core.management.base import BaseCommand
from notes.models import Note, TagSuggestion, TagSuggestionInputTag
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import pandas as pd


class Command(BaseCommand):
    help = "Build tag association rules and store them in TagSuggestion / TagSuggestionInputTag tables."

    def add_arguments(self, parser):
        parser.add_argument("--min_support", type=float, default=0.002)
        parser.add_argument("--min_confidence", type=float, default=0.1)

    def handle(self, *args, **options):
        min_support = options["min_support"]
        min_confidence = options["min_confidence"]

        self.stdout.write("Fetching notes and tags...")
        notes_with_tags = Note.fetch_bookmark_tags()
        transactions = list(notes_with_tags.values())

        if not transactions:
            self.stdout.write(self.style.WARNING("No notes found. Exiting."))
            return

        self.stdout.write(f"Running Apriori (min_support={min_support})...")

        te = TransactionEncoder()
        te_array = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_array, columns=te.columns_)

        frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)
        rules = association_rules(
            frequent_itemsets, metric="confidence", min_threshold=min_confidence
        )

        self.stdout.write(f"Found {len(rules)} rules. Saving to database...")

        TagSuggestion.objects.all().delete()
        TagSuggestionInputTag.objects.all().delete()

        seen = set()  # track (antecedents, suggested_tag) pairs
        objs = []
        input_tags_objs = []

        for _, row in rules.iterrows():
            antecedents = tuple(sorted(row["antecedents"]))  # canonical form
            for tag in row["consequents"]:
                key = (antecedents, tag)
                if key in seen:
                    continue
                seen.add(key)

                suggestion = TagSuggestion(
                    suggested_tag=tag,
                    confidence=row["confidence"],
                    lift=row["lift"],
                    support=row["support"],
                )
                objs.append((suggestion, antecedents))

        # Bulk insert TagSuggestions
        TagSuggestion.objects.bulk_create([s for s, _ in objs])

        # Reload with IDs
        all_suggestions = list(TagSuggestion.objects.all())
        for suggestion, antecedents in zip(all_suggestions, [a for _, a in objs]):
            for t in antecedents:
                input_tags_objs.append(TagSuggestionInputTag(suggestion=suggestion, tag=t))

        TagSuggestionInputTag.objects.bulk_create(input_tags_objs)

        # Reload them with IDs
        all_suggestions = list(TagSuggestion.objects.all())
        for suggestion, antecedents in zip(all_suggestions, [a for _, a in objs]):
            for t in antecedents:
                input_tags_objs.append(TagSuggestionInputTag(suggestion=suggestion, tag=t))

        TagSuggestionInputTag.objects.bulk_create(input_tags_objs)

        self.stdout.write(
            self.style.SUCCESS(f"Saved {len(all_suggestions)} tag suggestions.")
        )