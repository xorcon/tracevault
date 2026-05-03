"""Hybrid retrieval pipeline.

Orchestrates keyword and vector retrieval with score merging,
metadata filtering, and deterministic ranking.
"""

from tracevault.retrieval.audit import (
    build_response,
    generate_run_id,
    rank_candidates,
)
from tracevault.retrieval.interfaces import HybridRetriever, KeywordRetriever, VectorRetriever
from tracevault.retrieval.models import (
    RetrievalRequest,
    RetrievalResponse,
)
from tracevault.retrieval.scoring import HybridScoreMerger


class HybridRetrievalPipeline(HybridRetriever):
    """Full hybrid retrieval pipeline.

    Flow:
        1. Validate request
        2. Run keyword retrieval
        3. Run vector retrieval
        4. Apply metadata filters to both result sets
        5. Merge and deduplicate with hybrid scoring
        6. Rank with deterministic tie-breaking
        7. Return top-k results with audit metadata
    """

    def __init__(
        self,
        keyword_retriever: KeywordRetriever,
        vector_retriever: VectorRetriever,
        default_alpha: float = 0.5,
    ) -> None:
        super().__init__(keyword_retriever, vector_retriever)
        self.default_alpha = default_alpha

    def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Execute hybrid retrieval."""
        # Step 1: Validate
        errors = request.validate()
        if errors:
            raise ValueError(
                f"Invalid retrieval request: {'; '.join(errors)}"
            )

        # Generate run ID if not provided
        retrieval_run_id = request.retrieval_run_id or generate_run_id()
        query_hash = RetrievalRequest.compute_query_hash(request.query)

        # Convert filters
        metadata_filter = request.filters

        # Step 2: Run keyword retrieval
        keyword_results = self.keyword_retriever.retrieve(
            query=request.query,
            top_k=request.top_k * 2,
            filters=metadata_filter.to_dict() if metadata_filter else None,
        )

        # Step 3: Run vector retrieval
        vector_results = self.vector_retriever.retrieve(
            query=request.query,
            top_k=request.top_k * 2,
            filters=metadata_filter.to_dict() if metadata_filter else None,
        )

        # Count total candidates before merge
        total_candidates = len(set(
            (c.document_id, c.chunk_id)
            for c in keyword_results
        ) | set(
            (c.document_id, c.chunk_id)
            for c in vector_results
        ))

        # Step 4: Merge with hybrid scoring
        merger = HybridScoreMerger(alpha=request.alpha)
        merged = merger.merge(keyword_results, vector_results)

        # Step 5: Rank and select top-k
        results = rank_candidates(
            candidates=merged,
            retrieval_run_id=retrieval_run_id,
            query_hash=query_hash,
            top_k=request.top_k,
        )

        # Step 6: Build response
        return build_response(
            results=results,
            query=request.query,
            retrieval_run_id=retrieval_run_id,
            total_candidates=total_candidates,
            alpha=request.alpha,
            text_policy=request.text_policy,
            filters=metadata_filter,
        )
