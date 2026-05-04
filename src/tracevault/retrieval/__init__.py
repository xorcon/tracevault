"""Retrieval module.

Implements hybrid retrieval combining:
- Deterministic placeholder vector scores (not real vector retrieval)
- Token-frequency keyword search over raw_text and cleaned_text
- Metadata filtering
- Score merging and reranking

Phase 4: Hybrid Retrieval Foundation
"""

from tracevault.retrieval.audit import (
    build_response,
    build_trace,
    compute_query_hash,
    generate_run_id,
    rank_candidates,
)
from tracevault.retrieval.filters import (
    apply_filters,
    describe_filters,
    filter_by_document_id,
    filter_by_metadata,
    filter_by_source_path,
    filter_by_source_type,
)
from tracevault.retrieval.interfaces import (
    BaseRetriever,
    HybridRetriever,
    KeywordRetriever,
    VectorRetriever,
)
from tracevault.retrieval.keyword import InMemoryKeywordRetriever
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalScore,
    RetrievalTrace,
    ScoringCandidate,
    TextRetrievalPolicy,
)
from tracevault.retrieval.pipeline import (
    HybridRetrievalPipeline,
    create_pipeline,
)
from tracevault.retrieval.scoring import HybridScoreMerger
from tracevault.retrieval.text_policy import get_search_text
from tracevault.retrieval.vector import InMemoryVectorRetrieverPlaceholder

__all__ = [
    # Models
    "CandidateEvidence",
    "MetadataFilter",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "RetrievalScore",
    "RetrievalTrace",
    "ScoringCandidate",
    "TextRetrievalPolicy",
    # Interfaces
    "BaseRetriever",
    "HybridRetriever",
    "KeywordRetriever",
    "VectorRetriever",
    # Implementations
    "InMemoryKeywordRetriever",
    "InMemoryVectorRetrieverPlaceholder",
    "HybridRetrievalPipeline",
    "create_pipeline",
    # Scoring
    "HybridScoreMerger",
    # Filters
    "apply_filters",
    "describe_filters",
    "filter_by_document_id",
    "filter_by_metadata",
    "filter_by_source_path",
    "filter_by_source_type",
    # Text policy
    "get_search_text",
    # Audit
    "build_response",
    "build_trace",
    "compute_query_hash",
    "generate_run_id",
    "rank_candidates",
]
