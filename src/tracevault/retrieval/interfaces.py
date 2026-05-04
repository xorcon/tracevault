"""Retrieval interfaces.

Defines protocols for retrievers and the hybrid orchestration interface.
"""

from typing import Protocol, runtime_checkable

from tracevault.retrieval.models import (
    CandidateEvidence,
    RetrievalRequest,
    RetrievalResponse,
    ScoringCandidate,
    TextRetrievalPolicy,
)


@runtime_checkable
class BaseRetriever(Protocol):
    """Base protocol for any retriever.

    All retrievers must implement retrieve() and declare their source type.
    """

    source_type: str

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        text_policy: TextRetrievalPolicy | None = None,
    ) -> list[ScoringCandidate]:
        """Retrieve evidence candidates for a query.

        Args:
            query: Search query text.
            top_k: Maximum number of results to return.
            filters: Metadata filter criteria.
            text_policy: Per-request text policy override. If None, uses
                the retriever's constructor-time default.

        Returns:
            List of ScoringCandidate ranked by relevance.
        """
        ...


@runtime_checkable
class KeywordRetriever(BaseRetriever, Protocol):
    """Protocol for keyword-based retrievers.

    Keyword retrievers search over lexical tokens in raw_text and/or cleaned_text
    using token-frequency scoring.
    """

    source_type: str = "keyword"

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        text_policy: TextRetrievalPolicy | None = None,
    ) -> list[ScoringCandidate]:
        ...


@runtime_checkable
class VectorRetriever(BaseRetriever, Protocol):
    """Protocol for vector similarity retrievers.

    Future real vector retrievers will search over embeddings of cleaned_text.
    Phase 4 provides a deterministic placeholder — not real vector retrieval.
    """

    source_type: str = "vector"

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        text_policy: TextRetrievalPolicy | None = None,
    ) -> list[ScoringCandidate]:
        ...


class HybridRetriever:
    """Orchestration interface for hybrid retrieval.

    Combines keyword and vector retrieval with score merging and ranking.
    This is an abstract interface — concrete implementations must provide
    the keyword_retriever and vector_retriever and implement retrieve().
    """

    def __init__(
        self,
        keyword_retriever: KeywordRetriever,
        vector_retriever: VectorRetriever,
    ) -> None:
        self.keyword_retriever = keyword_retriever
        self.vector_retriever = vector_retriever

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Execute hybrid retrieval.

        Args:
            request: RetrievalRequest with query, top_k, alpha, filters, text_policy.

        Returns:
            RetrievalResponse with ranked results and audit metadata.

        Raises:
            ValueError: If request validation fails.
        """
        raise NotImplementedError
