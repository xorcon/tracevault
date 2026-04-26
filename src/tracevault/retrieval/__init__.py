"""Retrieval module.

Implements hybrid retrieval combining:
- Vector search over cleaned_text
- BM25/keyword search over raw_text and cleaned_text
- Metadata filtering
- Score merging and reranking

Phase 4 will implement the full hybrid retrieval pipeline.
"""

from typing import Protocol, TypedDict, runtime_checkable


class EvidenceItem(TypedDict):
    """Retrieved evidence item."""
    chunk_id: str
    document_id: str
    raw_text: str
    cleaned_text: str
    score: float
    retrieval_source: str  # 'vector', 'keyword', or 'hybrid'
    metadata: dict


@runtime_checkable
class Retriever(Protocol):
    """Protocol for hybrid retrieval."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        filters: dict | None = None
    ) -> list[EvidenceItem]:
        """Retrieve evidence for a query.

        Args:
            query: Search query.
            top_k: Maximum results to return.
            alpha: Hybrid weight (0=BM25 only, 1=vector only).
            filters: Metadata filters.

        Returns:
            List of evidence items ranked by relevance.
        """
        ...

    def build_evidence_pack(self, evidence_items: list[EvidenceItem]) -> dict:
        """Build structured evidence pack for reasoning.

        Args:
            evidence_items: Retrieved evidence items.

        Returns:
            Structured context for the reasoning model.
        """
        ...
