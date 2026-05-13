"""Metadata filtering for retrieval.

Applies MetadataFilter criteria to narrow the retrieval corpus.
"""

from tracevault.retrieval.models import CandidateEvidence, MetadataFilter


def apply_filters(
    candidates: list[CandidateEvidence],
    filters: MetadataFilter | None,
) -> list[CandidateEvidence]:
    """Apply metadata filters to a list of candidates.

    Args:
        candidates: List of CandidateEvidence to filter.
        filters: MetadataFilter criteria, or None for no filtering.

    Returns:
        Filtered list of candidates that match all filter criteria.
    """
    if filters is None or filters.is_empty():
        return list(candidates)
    return [c for c in candidates if filters.matches(c)]


def filter_by_document_id(
    candidates: list[CandidateEvidence],
    document_id: str,
) -> list[CandidateEvidence]:
    """Filter candidates by exact document_id match."""
    return [c for c in candidates if c.document_id == document_id]


def filter_by_source_path(
    candidates: list[CandidateEvidence],
    source_path: str,
) -> list[CandidateEvidence]:
    """Filter candidates by exact source_path match."""
    return [c for c in candidates if c.source_path == source_path]


def filter_by_source_type(
    candidates: list[CandidateEvidence],
    source_type: str,
) -> list[CandidateEvidence]:
    """Filter candidates by exact source_type match."""
    return [c for c in candidates if c.source_type == source_type]


def filter_by_metadata(
    candidates: list[CandidateEvidence],
    key: str,
    value: str,
) -> list[CandidateEvidence]:
    """Filter candidates by a metadata key/value pair."""
    return [c for c in candidates if c.metadata.get(key) == value]


def describe_filters_list(filters: MetadataFilter | None) -> list[str]:
    """Return a list of filter descriptions.

    Each filter is represented as a single string "key=value".
    This avoids lossy parsing when values contain ", ".
    """
    if filters is None or filters.is_empty():
        return []
    parts = []
    if filters.document_id is not None:
        parts.append(f"document_id={filters.document_id}")
    if filters.source_path is not None:
        parts.append(f"source_path={filters.source_path}")
    if filters.source_type is not None:
        parts.append(f"source_type={filters.source_type}")
    for key, value in filters.key_value.items():
        parts.append(f"{key}={value}")
    return parts


def describe_filters(filters: MetadataFilter | None) -> str:
    """Return a human-readable description of applied filters.

    Filters are joined with ", ". Use describe_filters_list() when
    you need to preserve individual filter entries (e.g., for audit traces).
    """
    return ", ".join(describe_filters_list(filters))
