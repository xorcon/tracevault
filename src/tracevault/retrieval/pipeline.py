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
from tracevault.retrieval.keyword import InMemoryKeywordRetriever
from tracevault.retrieval.models import (
    RetrievalRequest,
    RetrievalResponse,
    TextRetrievalPolicy,
)
from tracevault.retrieval.scoring import HybridScoreMerger
from tracevault.retrieval.vector import InMemoryVectorRetrieverPlaceholder


class HybridRetrievalPipeline(HybridRetriever):
    """Full hybrid retrieval pipeline.

    Flow:
        1. Validate request
        2. Run keyword retrieval (with text_policy)
        3. Run vector placeholder retrieval
        4. Merge and deduplicate with hybrid scoring
        5. Construct per-result RetrievalTrace with applied_filters
        6. Rank with deterministic tie-breaking
        7. Return top-k results with audit metadata

    text_policy enforcement:
        - text_policy is passed to the keyword retriever, which selects
          search text based on the policy.
        - text_policy does NOT remove raw_text from results — raw_text
          is always preserved as the authoritative source of truth.
        - Pipeline owns a default_text_policy (DUAL_CONTEXT by default).
          request.text_policy overrides it. The pipeline must NOT depend
          on keyword_retriever.text_policy existing.

    retrieval_run_id:
        - If request.retrieval_run_id is provided, it is used.
        - Otherwise, a random run ID is generated via generate_run_id().
        - Tests requiring deterministic responses should pass explicit
          retrieval_run_id.
    """

    def __init__(
        self,
        keyword_retriever: KeywordRetriever | None = None,
        vector_retriever: VectorRetriever | None = None,
        default_text_policy: TextRetrievalPolicy | None = None,
    ) -> None:
        # Allow construction without retrievers for testing
        kw = keyword_retriever or InMemoryKeywordRetriever([])
        vec = vector_retriever or InMemoryVectorRetrieverPlaceholder([])
        super().__init__(kw, vec)
        self.default_text_policy = default_text_policy or TextRetrievalPolicy.dual_context()

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

        # Convert filters — to_dict() flattens key_value into top level
        filters_dict = request.filters.to_dict() if request.filters else None

        # Determine effective text policy — request overrides pipeline default
        effective_text_policy = request.text_policy or self.default_text_policy

        # Step 2: Run keyword retrieval with effective text_policy
        keyword_results = self.keyword_retriever.retrieve(
            query=request.query,
            top_k=request.top_k * 2,
            filters=filters_dict,
            text_policy=effective_text_policy,
        )

        # Step 3: Run vector placeholder retrieval
        vector_results = self.vector_retriever.retrieve(
            query=request.query,
            top_k=request.top_k * 2,
            filters=filters_dict,
        )

        # Count total candidates before merge
        total_candidates = len(set(
            (s.candidate.document_id, s.candidate.chunk_id)
            for s in keyword_results
        ) | set(
            (s.candidate.document_id, s.candidate.chunk_id)
            for s in vector_results
        ))

        # Step 4: Merge with hybrid scoring
        merger = HybridScoreMerger(alpha=request.alpha)
        merged = merger.merge(keyword_results, vector_results)

        # Step 5: Rank with trace construction
        results = rank_candidates(
            candidates=merged,
            retrieval_run_id=retrieval_run_id,
            query_hash=query_hash,
            top_k=request.top_k,
            filters=request.filters,
        )

        # Step 6: Build response
        return build_response(
            results=results,
            query=request.query,
            retrieval_run_id=retrieval_run_id,
            total_candidates=total_candidates,
            alpha=request.alpha,
            text_policy=effective_text_policy,
            filters=request.filters,
        )


def create_pipeline(
    corpus: list,
    text_policy: TextRetrievalPolicy | None = None,
) -> HybridRetrievalPipeline:
    """Create a HybridRetrievalPipeline with in-memory retrievers.

    Args:
        corpus: List of CandidateEvidence to search over.
        text_policy: Controls which text fields are used for search.
    """
    kw = InMemoryKeywordRetriever(corpus, text_policy=text_policy)
    vec = InMemoryVectorRetrieverPlaceholder(corpus)
    return HybridRetrievalPipeline(kw, vec, default_text_policy=text_policy)
