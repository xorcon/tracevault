"""Audit metadata helpers for retrieval.

Generates and attaches audit metadata to retrieval results.
"""

import hashlib
import uuid

from tracevault.retrieval.filters import describe_filters
from tracevault.retrieval.models import (
    CandidateEvidence,
    MetadataFilter,
    RetrievalResponse,
    RetrievalResult,
    RetrievalTrace,
    TextRetrievalPolicy,
)


def generate_run_id() -> str:
    """Generate a unique retrieval run ID."""
    return f"run_{uuid.uuid4().hex[:16]}"


def compute_query_hash(query: str) -> str:
    """Compute SHA-256 hash of the query string."""
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def compute_cleaned_text_hash(cleaned_text: str) -> str:
    """Compute SHA-256 hash of cleaned text."""
    return hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()


def build_trace(
    candidate: CandidateEvidence,
    retrieval_source: str,
    matched_fields: list[str],
    filters: MetadataFilter | None,
) -> RetrievalTrace:
    """Build a RetrievalTrace for a candidate."""
    applied = []
    if filters:
        applied = describe_filters(filters).split(", ") if describe_filters(filters) else []

    return RetrievalTrace(
        document_id=candidate.document_id,
        chunk_id=candidate.chunk_id,
        source_path=candidate.source_path,
        raw_text_hash=candidate.raw_text_hash,
        cleaned_text_hash=candidate.cleaned_text_hash,
        retrieval_source=retrieval_source,
        matched_fields=matched_fields,
        applied_filters=applied,
    )


def rank_candidates(
    candidates: list[CandidateEvidence],
    retrieval_run_id: str,
    query_hash: str,
    top_k: int,
) -> list[RetrievalResult]:
    """Rank candidates and wrap them in RetrievalResult."""
    return [
        RetrievalResult(
            rank=i + 1,
            candidate=candidates[i],
            retrieval_run_id=retrieval_run_id,
            query_hash=query_hash,
        )
        for i in range(min(top_k, len(candidates)))
    ]


def build_response(
    results: list[RetrievalResult],
    query: str,
    retrieval_run_id: str,
    total_candidates: int,
    alpha: float,
    text_policy: TextRetrievalPolicy,
    filters: MetadataFilter | None,
) -> RetrievalResponse:
    """Build a RetrievalResponse from ranked results."""
    return RetrievalResponse(
        retrieval_run_id=retrieval_run_id,
        query=query,
        query_hash=compute_query_hash(query),
        results=results,
        total_candidates=total_candidates,
        alpha=alpha,
        text_policy=text_policy,
        applied_filters=describe_filters(filters),
    )
