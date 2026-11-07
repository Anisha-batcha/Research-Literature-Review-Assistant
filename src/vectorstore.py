"""Lightweight keyword retrieval for paper abstracts.

This BM25-style ranker keeps retrieval local without loading a neural model,
which allows searches to run on small free-tier instances.
"""

import math
import re
from collections import Counter


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return TOKEN_PATTERN.findall(text.lower())


def build_index(documents):
    """Prepare token counts and document lengths for keyword ranking."""
    tokenized = [_tokens(document) for document in documents]
    return {
        "documents": tokenized,
        "term_counts": [Counter(document) for document in tokenized],
        "lengths": [len(document) for document in tokenized],
        "average_length": (
            sum(map(len, tokenized)) / len(tokenized) if tokenized else 0
        ),
    }


def search_index(index, query, k=3):
    """Return document indices ranked by BM25-style query term relevance."""
    documents = index["documents"]
    if not documents or k <= 0:
        return [], []

    query_terms = set(_tokens(query))
    document_frequency = Counter(
        term
        for term in query_terms
        for counts in index["term_counts"]
        if counts.get(term, 0)
    )
    total_documents = len(documents)
    average_length = index["average_length"] or 1
    scores = []

    for doc_index, counts in enumerate(index["term_counts"]):
        length = index["lengths"][doc_index]
        score = 0.0
        for term in query_terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            df = document_frequency[term]
            inverse_document_frequency = math.log(
                1 + (total_documents - df + 0.5) / (df + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * length / average_length
            )
            score += inverse_document_frequency * frequency * 2.2 / denominator
        scores.append(score)

    ranked = sorted(range(total_documents), key=lambda i: (-scores[i], i))[:k]
    return ranked, [scores[i] for i in ranked]
