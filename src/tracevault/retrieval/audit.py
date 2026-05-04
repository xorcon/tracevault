"""Audit metadata helpers for retrieval.

Generates and attaches audit metadata to retrieval results.
"""

import hashlib
import uuid

from tracevault.retrieval.filters import describe_filters
from tracevault.retrieval.models import (
    MetadataFilter,
    RetrievalResponse,
    RetrievalResult,
    RetrievalTrace,
    ScoringCandidate,
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
    scoring: ScoringCandidate,
    filters: MetadataFilter | None,
) -> RetrievalTrace:
    """Build a RetrievalTrace from a ScoringCandidate.

    Reads retrieval_source, matched_fields, and source_retrievers
    from the ScoringCandidate's explicit trace fields — not from
    mutable candidate.metadata.
    """
    applied = []
    if filters:
        desc = describe_filters(filters)
        if desc:
            applied = desc.split(", ")

    c = scoring.candidate
    return RetrievalTrace(
        document_id=c.document_id,
        chunk_id=c.chunk_id,
        source_path=c.source_path,
        raw_text_hash=c.raw_text_hash,
        cleaned_text_hash=c.cleaned_text_hash,
        retrieval_source=scoring.retrieval_source,
        matched_fields=scoring.matched_fields,
        applied_filters=applied,
        score_policy=c.score.score_policy,
        source_retrievers=scoring.source_retrievers,
    )


def rank_candidates(
    candidates: list[ScoringCandidate],
    retrieval_run_id: str,
    query_hash: str,
    top_k: int,
    filters: MetadataFilter | None,
) -> list[RetrievalResult]:
    """Rank ScoringCandidates and wrap them in RetrievalResult with trace."""
    results = []
    for i in range(min(top_k, len(candidates))):
        s = candidates[i]
        trace = build_trace(s, filters)
        results.append(
            RetrievalResult(
                rank=i + 1,
                candidate=s.candidate,
                retrieval_run_id=retrieval_run_id,
                query_hash=query_hash,
                trace=trace,
            )
        )
    return results


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
