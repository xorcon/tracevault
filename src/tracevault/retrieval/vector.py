"""In-memory vector retriever placeholder.

Provides deterministic fixture-based scores for testing.
Does NOT perform real vector retrieval, embedding, or semantic similarity.
"""

import hashlib

from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalScore,
    ScoringCandidate,
    TextRetrievalPolicy,
)


def _deterministic_score(
    query: str,
    chunk_id: str,
) -> float:
    """Generate a deterministic pseudo-score from query and chunk_id.

    Uses a hash-based approach to produce a reproducible score in [0.0, 1.0].
    Does NOT compute semantic similarity or use embeddings.
    """
    combined = f"{query}:{chunk_id}"
    hash_value = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    int_value = int(hash_value[:8], 16)
    max_value = 0xFFFFFFFF
    return int_value / max_value


class InMemoryVectorRetrieverPlaceholder:
    """Deterministic placeholder for vector retrieval.

    Uses hash-based scores from query + chunk_id. Does NOT:
    - Call any embedding model
    - Query any vector database
    - Compute semantic similarity
    - Inspect document text

    This exists solely to allow pipeline testing without external dependencies.
    """

    source_type = "vector_placeholder"

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
        text_policy: TextRetrievalPolicy | None = None,
    ) -> list[ScoringCandidate]:
        """Retrieve candidates using deterministic placeholder scores.

        Args:
            query: Search query text.
            top_k: Maximum number of results to return.
            filters: Metadata filter criteria.
            text_policy: Unused by the placeholder, accepted for protocol compatibility.
        """
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

        scored: list[ScoringCandidate] = []
        for candidate in self.corpus:
            if metadata_filter and not metadata_filter.matches(candidate):
                continue

            score = _deterministic_score(query, candidate.chunk_id)

            scored.append(
                ScoringCandidate(
                    candidate=candidate,
                    score=RetrievalScore(
                        keyword_score=0.0,
                        vector_score=score,
                        hybrid_score=score,
                        alpha=1.0,
                        score_policy="deterministic_placeholder",
                    ),
                    matched_fields=[],
                    retrieval_source="vector_placeholder",
                    source_retrievers=["vector_placeholder"],
                )
            )

        # Sort by vector_score desc, then document_id asc, chunk_id asc
        scored.sort(
            key=lambda s: (
                -s.score.vector_score,
                s.candidate.document_id,
                s.candidate.chunk_id,
            )
        )

        return scored[:top_k]
