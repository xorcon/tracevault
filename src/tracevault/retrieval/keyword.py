"""In-memory keyword retriever.

Implements keyword-based retrieval over raw_text and/or cleaned_text
using token-frequency scoring.
"""

import re
from collections import Counter

from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalScore,
    ScoringCandidate,
    TextRetrievalPolicy,
)
from tracevault.retrieval.text_policy import get_search_text


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _compute_keyword_score(
    query_tokens: list[str],
    doc_tokens: list[str],
) -> float:
    """Compute a normalized keyword relevance score.

    Uses token-frequency with saturation and simple length normalization.
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_counter = Counter(doc_tokens)
    doc_length = len(doc_tokens)

    score = 0.0
    for token in query_tokens:
        freq = doc_counter.get(token, 0)
        if freq > 0:
            # Term frequency with saturation
            tf = (freq * 1.5) / (freq + 0.5)
            score += tf

    # Normalize by document length
    normalized = score / (1 + doc_length * 0.001)

    # Clamp to [0, 1]
    return min(1.0, normalized)


class InMemoryKeywordRetriever:
    """In-memory keyword retriever over a corpus of CandidateEvidence.

    Searches over raw_text and/or cleaned_text based on TextRetrievalPolicy
    using deterministic token-frequency scoring.
    """

    source_type = "keyword"

    def __init__(
        self,
        corpus: list[CandidateEvidence],
        text_policy: TextRetrievalPolicy | None = None,
    ) -> None:
        self.corpus = list(corpus)
        self.text_policy = text_policy or TextRetrievalPolicy.dual_context()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        text_policy: TextRetrievalPolicy | None = None,
    ) -> list[ScoringCandidate]:
        """Retrieve candidates using keyword matching.

        Args:
            query: Search query text.
            top_k: Maximum number of results to return.
            filters: Metadata filter criteria.
            text_policy: Per-request text policy override. If None, uses
                the retriever's constructor-time default.
        """
        if not query.strip():
            return []

        # Per-request policy overrides constructor default
        effective_policy = text_policy or self.text_policy

        query_tokens = _tokenize(query)

        # Build filter if provided
        metadata_filter = None
        if filters:
            metadata_filter = MetadataFilter(
                document_id=filters.get("document_id"),
                source_path=filters.get("source_path"),
                source_type=filters.get("source_type"),
                key_value={k: v for k, v in filters.items() if k not in ("document_id", "source_path", "source_type")},
            )

        # Score each candidate
        scored: list[ScoringCandidate] = []
        for candidate in self.corpus:
            # Apply filter
            if metadata_filter and not metadata_filter.matches(candidate):
                continue

            # Get search text based on effective policy
            search_text = get_search_text(candidate, effective_policy)
            doc_tokens = _tokenize(search_text)

            score = _compute_keyword_score(query_tokens, doc_tokens)

            if score > 0:
                # Determine matched fields using effective policy
                matched_fields = []
                if effective_policy.uses_raw():
                    raw_tokens = _tokenize(candidate.raw_text)
                    if any(t in Counter(raw_tokens) for t in query_tokens):
                        matched_fields.append("raw_text")
                if effective_policy.uses_cleaned():
                    cleaned_tokens = _tokenize(candidate.cleaned_text)
                    if any(t in Counter(cleaned_tokens) for t in query_tokens):
                        matched_fields.append("cleaned_text")

                scored.append(
                    ScoringCandidate(
                        candidate=candidate,
                        score=RetrievalScore(
                            keyword_score=score,
                            vector_score=0.0,
                            hybrid_score=score,
                            alpha=0.0,
                            score_policy="token_frequency",
                        ),
                        matched_fields=matched_fields,
                        retrieval_source="keyword",
                        source_retrievers=["keyword"],
                    )
                )

        # Sort by keyword_score desc, then document_id asc, chunk_id asc
        scored.sort(
            key=lambda s: (
                -s.score.keyword_score,
                s.candidate.document_id,
                s.candidate.chunk_id,
            )
        )

        return scored[:top_k]
