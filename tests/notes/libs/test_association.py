"""Tests for notes.libs.association.suggest_tags."""

from django.test import TestCase

from notes.libs.association import suggest_tags
from notes.models import TagSuggestion, TagSuggestionInputTag


class SuggestTagsTests(TestCase):
    def _make_suggestion(self, antecedents, suggested_tag, confidence, lift=1.0, support=0.5):
        suggestion = TagSuggestion.objects.create(
            suggested_tag=suggested_tag, confidence=confidence, lift=lift, support=support
        )
        for tag in antecedents:
            TagSuggestionInputTag.objects.create(suggestion=suggestion, tag=tag)
        return suggestion

    def test_returns_a_suggestion_whose_antecedents_are_all_present(self):
        self._make_suggestion(["alpha"], "beta", confidence=0.8)

        assert suggest_tags(["alpha"]) == ["beta"]

    def test_no_match_when_an_antecedent_is_missing(self):
        self._make_suggestion(["alpha", "gamma"], "beta", confidence=0.8)

        assert suggest_tags(["alpha"]) == []

    def test_suggested_tag_already_present_is_excluded(self):
        self._make_suggestion(["alpha"], "beta", confidence=0.8)

        assert suggest_tags(["alpha", "beta"]) == []

    def test_extra_input_tags_beyond_the_antecedents_are_fine(self):
        self._make_suggestion(["alpha"], "beta", confidence=0.8)

        assert suggest_tags(["alpha", "unrelated"]) == ["beta"]

    def test_duplicate_suggested_tags_keep_only_the_highest_confidence_one(self):
        self._make_suggestion(["alpha"], "beta", confidence=0.4, lift=1.0)
        self._make_suggestion(["alpha"], "beta", confidence=0.9, lift=2.0)

        result = suggest_tags(["alpha"])

        assert result == ["beta"]
        kept = TagSuggestion.objects.get(suggested_tag="beta", confidence=0.9)
        assert kept.lift == 2.0

    def test_results_are_sorted_by_confidence_then_lift_descending(self):
        self._make_suggestion(["alpha"], "low", confidence=0.3, lift=5.0)
        self._make_suggestion(["alpha"], "high", confidence=0.9, lift=1.0)
        self._make_suggestion(["alpha"], "mid", confidence=0.6, lift=1.0)

        assert suggest_tags(["alpha"]) == ["high", "mid", "low"]

    def test_ties_on_confidence_are_broken_by_lift(self):
        self._make_suggestion(["alpha"], "low-lift", confidence=0.7, lift=1.0)
        self._make_suggestion(["alpha"], "high-lift", confidence=0.7, lift=3.0)

        assert suggest_tags(["alpha"]) == ["high-lift", "low-lift"]

    def test_results_are_capped_at_top_n(self):
        for i in range(5):
            self._make_suggestion(["alpha"], f"tag{i}", confidence=0.1 * i)

        assert len(suggest_tags(["alpha"], top_n=2)) == 2

    def test_no_suggestions_at_all_returns_empty_list(self):
        assert suggest_tags(["alpha"]) == []

    def test_a_suggestion_with_no_antecedents_matches_any_input(self):
        # An empty antecedent set is a subset of everything, including an
        # empty input - this documents that "no rule input" is trivially
        # satisfied rather than being treated as unmatchable.
        self._make_suggestion([], "beta", confidence=0.5)

        assert suggest_tags([]) == ["beta"]
