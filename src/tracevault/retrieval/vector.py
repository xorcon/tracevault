"""In-memory vector retriever placeholder.

Provides deterministic fixture-based vector scores without requiring
an actual embedding model or vector database.
"""

import hashlib

from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalScore,
    RetrievalTrace,
)


def _deterministic_score(
    query: str,
    chunk_id: str,
) -> float:
    """Generate a deterministic pseudo-vector score from query and chunk_id.

    Uses a hash-based approach to produce a reproducible score in [0.0, 1.0].
    """
    combined = f"{query}:{chunk_id}"
    hash_value = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    int_value = int(hash_value[:8], 16)
    max_value = 0xFFFFFFFF
    return int_value / max_value


class InMemoryVectorRetrieverPlaceholder:
    """Placeholder vector retriever using deterministic fixture scores.

    Does NOT call any embedding model or vector database.
    """

    source_type = "vector"

    def __init__(
        self,
        corpus: list[CandidateEvidence],
    ) -> None:
        self.corpus = list(corpus)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[CandidateEvidence]:
        """Retrieve candidates using deterministic placeholder vector scores."""
        if not query.strip():
            return []

        # Build filter if provided
        metadata_filter = None
        if filters:
            metadata_filter = MetadataFilter(
                document_id=filters.get("document_id"),
                source_path=filters.get("source_path"),
                source_type=filters.get("source_type"),
                key_value={k: v for k, v in filters.items() if k not in ("document_id", "source_path", "source_type")},
            )

        scored = []
        for candidate in self.corpus:
            if metadata_filter and not metadata_filter.matches(candidate):
                continue

            score = _deterministic_score(query, candidate.chunk_id)

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
                    keyword_score=0.0,
                    vector_score=score,
                    hybrid_score=score,
                    alpha=1.0,
                ),
                trace=RetrievalTrace(
                    document_id=candidate.document_id,
                    chunk_id=candidate.chunk_id,
                    source_path=candidate.source_path,
                    raw_text_hash=candidate.raw_text_hash,
                    cleaned_text_hash=candidate.cleaned_text_hash,
                    retrieval_source="vector",
                    matched_fields=["cleaned_text"],
                ),
                metadata=candidate.metadata,
            )
            scored.append(result)

        # Sort by vector_score desc, then document_id asc, chunk_id asc
        scored.sort(key=lambda c: (-c.score.vector_score, c.document_id, c.chunk_id))

        return scored[:top_k]
