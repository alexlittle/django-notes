
from notes.models import TagSuggestion

def suggest_tags(input_tags, top_n=5):
    input_set = set(input_tags)

    best = {}  # suggested_tag -> best TagSuggestion

    for s in TagSuggestion.objects.exclude(suggested_tag__in=input_tags):
        antecedents = set(s.input_tags.values_list("tag", flat=True))
        if antecedents.issubset(input_set):
            # keep only the highest confidence version
            if (s.suggested_tag not in best) or (s.confidence > best[s.suggested_tag].confidence):
                best[s.suggested_tag] = s

    # now best.values() are unique TagSuggestion objects
    suggestions = list(best.values())

    # Sort by confidence + lift
    suggestions.sort(key=lambda x: (x.confidence, x.lift), reverse=True)
    return [s.suggested_tag for s in suggestions[:top_n]]