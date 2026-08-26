from django.core.management import call_command

from notes.models import TagSuggestion, TagSuggestionInputTag

from .base import NotesCommandTestCase


class BuildTagSuggestionsCommandTests(NotesCommandTestCase):
    def _make_bookmarks(self, count, tags, title_prefix="Bookmark"):
        for i in range(count):
            self.make_bookmark(tags=tags, title=f"{title_prefix} {i}")

    def _make_correlated_dataset(self):
        # 20 bookmarks total:
        #   10 tagged [alpha, beta]
        #    5 tagged [alpha] only
        #    5 tagged [gamma] only (unrelated noise)
        # support(alpha)=15/20=0.75, support(beta)=10/20=0.5,
        # support(alpha&beta)=10/20=0.5
        # confidence(alpha->beta)=0.5/0.75=0.667, confidence(beta->alpha)=0.5/0.5=1.0
        alpha = self.make_tag(name="alpha")
        beta = self.make_tag(name="beta")
        gamma = self.make_tag(name="gamma")
        self._make_bookmarks(10, [alpha, beta], "Both")
        self._make_bookmarks(5, [alpha], "AlphaOnly")
        self._make_bookmarks(5, [gamma], "GammaOnly")

    def test_no_bookmarks_returns_early_without_touching_existing_suggestions(self):
        # The early-return for "no transactions" happens before the
        # delete-and-rebuild step, so anything already in these tables is
        # left completely alone.
        stale = TagSuggestion.objects.create(
            suggested_tag="stale", confidence=0.5, lift=1.0, support=0.5
        )

        call_command("build_tag_suggestions")

        self.assertTrue(TagSuggestion.objects.filter(pk=stale.pk).exists())

    def test_only_bookmark_type_notes_contribute_transactions(self):
        self._make_correlated_dataset()
        noise = self.make_tag(name="noise")
        for i in range(5):
            note = self.make_note(type="task", title=f"Task {i}")
            self.tag_note(note, noise)

        call_command("build_tag_suggestions")

        suggested_tags = set(TagSuggestion.objects.values_list("suggested_tag", flat=True))
        self.assertNotIn("noise", suggested_tags)
        input_tags = set(TagSuggestionInputTag.objects.values_list("tag", flat=True))
        self.assertNotIn("noise", input_tags)

    def test_generates_a_suggestion_from_a_correlated_tag_pair(self):
        self._make_correlated_dataset()

        call_command("build_tag_suggestions")

        suggestion = TagSuggestion.objects.get(suggested_tag="beta")
        input_tags = set(
            TagSuggestionInputTag.objects.filter(suggestion=suggestion).values_list(
                "tag", flat=True
            )
        )
        self.assertEqual(input_tags, {"alpha"})
        self.assertAlmostEqual(suggestion.support, 0.5, places=4)
        self.assertAlmostEqual(suggestion.confidence, 0.6667, places=3)

    def test_existing_suggestions_are_replaced_not_accumulated(self):
        self._make_correlated_dataset()
        stale = TagSuggestion.objects.create(
            suggested_tag="old-stale-suggestion", confidence=0.9, lift=2.0, support=0.9
        )

        call_command("build_tag_suggestions")

        self.assertFalse(TagSuggestion.objects.filter(pk=stale.pk).exists())

    def test_raising_min_confidence_filters_out_weaker_rules(self):
        self._make_correlated_dataset()

        # confidence(alpha->beta)=0.667, confidence(beta->alpha)=1.0
        call_command("build_tag_suggestions", min_confidence=0.9)

        suggested_tags = set(TagSuggestion.objects.values_list("suggested_tag", flat=True))
        self.assertEqual(suggested_tags, {"alpha"})

    def test_a_min_support_high_enough_to_exclude_everything_currently_crashes(self):
        # When min_support filters out every itemset, frequent_itemsets
        # ends up empty, and mlxtend's association_rules() raises
        # ValueError rather than the command handling it gracefully (it
        # only guards the "no transactions at all" case, not "transactions
        # exist but nothing meets the threshold"). See README for a
        # suggested one-line fix.
        self._make_correlated_dataset()

        with self.assertRaises(ValueError):
            call_command("build_tag_suggestions", min_support=0.9)
