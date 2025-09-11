import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules

from notes.models import Note

def build_rules(min_support=0.002, min_confidence=0.5):
    """
    Build association rules from tagged notes.
    :param min_support: minimum support for frequent itemsets
    :param min_confidence: minimum confidence for association rules
    :return: DataFrame of rules
    """
    notes = Note.fetch_bookmark_tags()
    transactions = list(notes.values())

    # One-hot encode
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(te_array, columns=te.columns_)

    # Frequent itemsets
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)

    # Association rules
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
    return rules


def suggest_tags(rules, input_tags, top_n=5):
    """
    Suggest related tags given a set of input tags.
    :param rules: association rules DataFrame
    :param input_tags: list of tags to check
    :param top_n: number of suggestions
    :return: DataFrame of suggested tags with scores
    """
    input_set = frozenset(input_tags)

    # Find rules where antecedents ⊆ input_tags
    matches = rules[rules['antecedents'].apply(lambda a: a.issubset(input_set))]

    # Exclude consequents that overlap with input_tags
    matches = matches[matches['consequents'].apply(lambda c: c.isdisjoint(input_set))]

    # Flatten consequents into (tag, confidence) pairs
    suggestions = []
    for _, row in matches.iterrows():
        for tag in row['consequents']:
            suggestions.append((tag, row['confidence']))

    # Deduplicate by keeping the highest confidence for each tag
    best_conf = {}
    for tag, conf in suggestions:
        if tag not in best_conf or conf > best_conf[tag]:
            best_conf[tag] = conf

    # Sort by confidence, descending
    ordered_tags = sorted(best_conf.items(), key=lambda x: x[1], reverse=True)

    # Return just the tag names
    return [tag for tag, _ in ordered_tags[:top_n]]