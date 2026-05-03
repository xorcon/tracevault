"""In-memory keyword retriever.

Implements keyword-based retrieval over raw_text and/or cleaned_text
using simple token frequency scoring.
"""

import re
from collections import Counter

from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalScore,
    RetrievalTrace,
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

    Uses a simplified BM25-like approach with term frequency saturation.
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_counter = Counter(doc_tokens)
    doc_length = len(doc_tokens)

    score = 0.0
    for token in query_tokens:
        freq = doc_counter.get(token, 0)
        if freq > 0:
            # BM25-like term frequency with saturation
            tf = (freq * 1.5) / (freq + 0.5)
            score += tf

    # Normalize by document length
    normalized = score / (1 + doc_length * 0.001)

    # Clamp to [0, 1]
    return min(1.0, normalized)


class InMemoryKeywordRetriever:
    """In-memory keyword retriever over a corpus of CandidateEvidence.

    Searches over raw_text and/or cleaned_text based on TextRetrievalPolicy.
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
    ) -> list[CandidateEvidence]:
        """Retrieve candidates using keyword matching."""
        if not query.strip():
            return []

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
        scored = []
        for candidate in self.corpus:
            # Apply filter
            if metadata_filter and not metadata_filter.matches(candidate):
                continue

            # Get search text based on policy
            search_text = get_search_text(candidate, self.text_policy)
            doc_tokens = _tokenize(search_text)

            score = _compute_keyword_score(query_tokens, doc_tokens)

            if score > 0:
                # Determine matched fields
                matched_fields = []
                if self.text_policy.uses_raw():
                    raw_tokens = _tokenize(candidate.raw_text)
                    if any(t in Counter(raw_tokens) for t in query_tokens):
                        matched_fields.append("raw_text")
                if self.text_policy.uses_cleaned():
                    cleaned_tokens = _tokenize(candidate.cleaned_text)
                    if any(t in Counter(cleaned_tokens) for t in query_tokens):
                        matched_fields.append("cleaned_text")

                result = CandidateEvidence(
                    document_id=candidate.document_id,
                    chunk_id=candidate.chunk_id,
                    chunk_index=candidate.chunk_index,
                    source_path=candidate.source_path,
                    source_type=candidate.source_type,
                    raw_text=candidate.raw_text,
                    cleaned_text=candidate.cleaned_text,
                    raw_text_hash=candidate.raw_text_hash,
                    cleaned_text_hash=candidate.cleaned_text_hash,
                    score=RetrievalScore(
                        keyword_score=score,
                        vector_score=0.0,
                        hybrid_score=score,
                        alpha=0.0,
                    ),
                    trace=RetrievalTrace(
                        document_id=candidate.document_id,
                        chunk_id=candidate.chunk_id,
                        source_path=candidate.source_path,
                        raw_text_hash=candidate.raw_text_hash,
                        cleaned_text_hash=candidate.cleaned_text_hash,
                        retrieval_source="keyword",
                        matched_fields=matched_fields,
                    ),
                    metadata=candidate.metadata,
                )
                scored.append(result)

        # Sort by keyword_score desc, then document_id asc, chunk_id asc
        scored.sort(key=lambda c: (-c.score.keyword_score, c.document_id, c.chunk_id))

        return scored[:top_k]
