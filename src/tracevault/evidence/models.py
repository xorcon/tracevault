"""Data models for evidence packs.

Defines structured types for evidence pack requests, responses, items,
groups, policies, budgets, and exclusions.

Key concepts:
- EvidencePackRequest: Input to the evidence pack builder
- EvidencePackResponse: Output of the evidence pack builder
- EvidencePack: The assembled evidence pack with items, context, and audit
- EvidenceItem: A single evidence item derived from a RetrievalResult
- EvidenceGroup: A named grouping of evidence items
- EvidencePackTrace: Full audit trail for an evidence pack
- EvidenceSelectionPolicy: Controls how evidence is selected and ordered
- ContextAssemblyPolicy: Controls what text is included in context
- EvidenceBudget: Character/item limits for evidence packs
- EvidenceExclusion: Records why an evidence item was excluded
- EvidenceExclusionReason: Mechanical reasons for exclusion
"""

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from tracevault.retrieval.models import (
    RetrievalResponse,
    RetrievalScore,
    TextRetrievalPolicy,
)


@dataclass(frozen=True)
class EvidenceExclusionReason:
    """Mechanical reason codes for evidence exclusion.

    Only mechanical, non-semantic reasons are used in Phase 5.
    """

    MAX_ITEMS_EXCEEDED: Literal["max_items_exceeded"] = "max_items_exceeded"
    MAX_RAW_CHARS_EXCEEDED: Literal["max_raw_chars_exceeded"] = "max_raw_chars_exceeded"
    MAX_CLEANED_CHARS_EXCEEDED: Literal["max_cleaned_chars_exceeded"] = "max_cleaned_chars_exceeded"
    MAX_CONTEXT_CHARS_EXCEEDED: Literal["max_context_chars_exceeded"] = "max_context_chars_exceeded"
    DUPLICATE_DOCUMENT_CHUNK: Literal["duplicate_document_chunk"] = "duplicate_document_chunk"
    DUPLICATE_RAW_TEXT_HASH: Literal["duplicate_raw_text_hash"] = "duplicate_raw_text_hash"


@dataclass(frozen=True)
class EvidenceBudget:
    """Character and item limits for evidence pack construction.

    All fields are optional. None means unlimited.
    Budget is enforced by excluding whole evidence items (no truncation).

    Attributes:
        max_items: Maximum number of evidence items
        max_raw_chars: Maximum total raw_text characters
        max_cleaned_chars: Maximum total cleaned_text characters
        max_context_chars: Maximum total context characters (raw + cleaned combined)
    """

    max_items: int | None = None
    max_raw_chars: int | None = None
    max_cleaned_chars: int | None = None
    max_context_chars: int | None = None

    def is_unlimited(self) -> bool:
        """Return True if no budget limits are set."""
        return (
            self.max_items is None
            and self.max_raw_chars is None
            and self.max_cleaned_chars is None
            and self.max_context_chars is None
        )


@dataclass(frozen=True)
class EvidenceSelectionPolicy:
    """Controls how evidence items are selected and ordered.

    Attributes:
        order_by: Sort order for evidence items. "retrieval_rank" uses
            the rank from RetrievalResult (default).
        deduplicate_by: Deduplication strategy. "document_chunk" deduplicates
            by (document_id, chunk_id). "raw_text_hash" deduplicates by
            raw_text_hash.
    """

    order_by: Literal["retrieval_rank"] = "retrieval_rank"
    deduplicate_by: Literal["document_chunk", "raw_text_hash"] = "document_chunk"

    def __post_init__(self):
        if self.order_by not in ("retrieval_rank",):
            raise ValueError(f"Invalid order_by: {self.order_by}")
        if self.deduplicate_by not in ("document_chunk", "raw_text_hash"):
            raise ValueError(f"Invalid deduplicate_by: {self.deduplicate_by}")


@dataclass(frozen=True)
class ContextAssemblyPolicy:
    """Controls what text fields are included in context assembly.

    Attributes:
        include_raw_text: Include raw_text in context assembly
        include_cleaned_text: Include cleaned_text in context assembly
    """

    include_raw_text: bool = True
    include_cleaned_text: bool = True


@dataclass(frozen=True)
class EvidenceExclusion:
    """Records why an evidence item was mechanically excluded.

    Attributes:
        document_id: The excluded item's document_id
        chunk_id: The excluded item's chunk_id
        reason: Mechanical exclusion reason code
        budget_field: Which budget field triggered the exclusion (for budget reasons)
        detail: Optional detail identifying the earlier selected duplicate
    """

    document_id: str
    chunk_id: str
    reason: str
    budget_field: str = ""
    detail: str = ""


@dataclass(frozen=True)
class EvidenceItem:
    """A single evidence item derived from a RetrievalResult.

    Preserves all traceability metadata from the retrieval layer.

    Attributes:
        document_id: Source document identifier
        chunk_id: Source chunk identifier
        chunk_index: Zero-based index within document
        source_path: Original file path
        source_type: File type (txt, md, etc.)
        raw_text: Original source text (source of truth)
        cleaned_text: Normalized text for retrieval
        raw_text_hash: SHA-256 of raw_text
        cleaned_text_hash: SHA-256 of cleaned_text (if available)
        retrieval_run_id: Unique identifier for the retrieval run
        query_hash: SHA-256 of the query string
        retrieval_source: Which retrieval path(s) returned this candidate
        source_retrievers: Which retrievers contributed scores
        matched_fields: Which text fields matched the query
        score: RetrievalScore with component scores
        rank: 1-based rank position from retrieval
        text_policy: TextRetrievalPolicy used during retrieval
        applied_filters: Filters that were applied during retrieval
        candidate_metadata: Original CandidateEvidence.metadata (read-only copy)
    """

    document_id: str
    chunk_id: str
    chunk_index: int
    source_path: str
    source_type: str
    raw_text: str
    cleaned_text: str
    raw_text_hash: str
    cleaned_text_hash: str | None = None
    retrieval_run_id: str = ""
    query_hash: str = ""
    retrieval_source: str = ""
    source_retrievers: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    score: RetrievalScore = field(default_factory=RetrievalScore)
    rank: int = 0
    text_policy: TextRetrievalPolicy = field(default_factory=TextRetrievalPolicy.dual_context)
    applied_filters: list[str] = field(default_factory=list)
    candidate_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "raw_text_hash": self.raw_text_hash,
            "cleaned_text_hash": self.cleaned_text_hash,
            "retrieval_run_id": self.retrieval_run_id,
            "query_hash": self.query_hash,
            "retrieval_source": self.retrieval_source,
            "source_retrievers": self.source_retrievers,
            "matched_fields": self.matched_fields,
            "score": self.score.to_dict(),
            "rank": self.rank,
            "text_policy": self.text_policy.mode,
            "applied_filters": self.applied_filters,
            "candidate_metadata": self.candidate_metadata,
        }


@dataclass(frozen=True)
class EvidenceGroup:
    """A named grouping of evidence items.

    Groups are mechanical groupings for context assembly — not semantic
    clustering.

    Attributes:
        group_name: Human-readable group identifier
        items: Evidence items in this group
    """

    group_name: str
    items: list[EvidenceItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "group_name": self.group_name,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class EvidencePackTrace:
    """Full audit trail for an evidence pack.

    Attributes:
        pack_id: Deterministic identifier for this evidence pack
        retrieval_run_id: The retrieval run that produced the source data
        query: Original query text
        query_hash: SHA-256 of the query
        total_input_results: Number of RetrievalResult items in the input
        total_selected_items: Number of evidence items after selection
        total_excluded_items: Number of excluded items
        exclusions: List of EvidenceExclusion records
        selection_policy: The EvidenceSelectionPolicy used
        context_policy: The ContextAssemblyPolicy used
        budget: The EvidenceBudget used
        text_policy: TextRetrievalPolicy from the retrieval response
        applied_filters: Verbatim applied_filters string from RetrievalResponse
        pack_run_id: Optional run identifier injected by the caller
    """

    pack_id: str
    retrieval_run_id: str
    query: str
    query_hash: str
    total_input_results: int
    total_selected_items: int
    total_excluded_items: int
    exclusions: list[EvidenceExclusion] = field(default_factory=list)
    selection_policy: EvidenceSelectionPolicy = field(default_factory=EvidenceSelectionPolicy)
    context_policy: ContextAssemblyPolicy = field(default_factory=ContextAssemblyPolicy)
    budget: EvidenceBudget | None = None
    text_policy: TextRetrievalPolicy = field(default_factory=TextRetrievalPolicy.dual_context)
    applied_filters: str = ""
    pack_run_id: str = ""

    def __post_init__(self):
        """Reject degenerate traces — audit fields must be non-empty."""
        if not self.pack_id:
            raise ValueError("EvidencePackTrace.pack_id must not be empty")
        if not self.retrieval_run_id:
            raise ValueError("EvidencePackTrace.retrieval_run_id must not be empty")
        if not self.query_hash:
            raise ValueError("EvidencePackTrace.query_hash must not be empty")

    def to_dict(self) -> dict:
        return {
            "pack_id": self.pack_id,
            "retrieval_run_id": self.retrieval_run_id,
            "query": self.query,
            "query_hash": self.query_hash,
            "total_input_results": self.total_input_results,
            "total_selected_items": self.total_selected_items,
            "total_excluded_items": self.total_excluded_items,
            "exclusions": [
                {
                    "document_id": e.document_id,
                    "chunk_id": e.chunk_id,
                    "reason": e.reason,
                    "budget_field": e.budget_field,
                    "detail": e.detail,
                }
                for e in self.exclusions
            ],
            "selection_policy": {
                "order_by": self.selection_policy.order_by,
                "deduplicate_by": self.selection_policy.deduplicate_by,
            },
            "context_policy": {
                "include_raw_text": self.context_policy.include_raw_text,
                "include_cleaned_text": self.context_policy.include_cleaned_text,
            },
            "budget": {
                "max_items": self.budget.max_items,
                "max_raw_chars": self.budget.max_raw_chars,
                "max_cleaned_chars": self.budget.max_cleaned_chars,
                "max_context_chars": self.budget.max_context_chars,
            }
            if self.budget
            else None,
            "text_policy": self.text_policy.mode,
            "applied_filters": self.applied_filters,
            "pack_run_id": self.pack_run_id,
        }


@dataclass(frozen=True)
class EvidencePack:
    """The assembled evidence pack with items, context, and audit trace.

    Attributes:
        items: Selected evidence items in deterministic order
        groups: Named groupings of evidence items
        context: Mechanical context assembly string
        trace: Full audit trail
    """

    trace: EvidencePackTrace
    items: list[EvidenceItem] = field(default_factory=list)
    groups: list[EvidenceGroup] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "groups": [g.to_dict() for g in self.groups],
            "context": self.context,
            "trace": self.trace.to_dict(),
        }


@dataclass(frozen=True)
class EvidencePackRequest:
    """Input to the evidence pack builder.

    Attributes:
        retrieval_response: The RetrievalResponse from the retrieval pipeline
        selection_policy: How to select and order evidence items
        context_policy: What text to include in context assembly
        budget: Optional character/item limits
        pack_run_id: Optional run identifier for the pack (deterministic if provided)
    """

    retrieval_response: RetrievalResponse
    selection_policy: EvidenceSelectionPolicy | None = None
    context_policy: ContextAssemblyPolicy | None = None
    budget: EvidenceBudget | None = None
    pack_run_id: str = ""


@dataclass(frozen=True)
class EvidencePackResponse:
    """Output of the evidence pack builder.

    Attributes:
        evidence_pack: The assembled EvidencePack
    """

    evidence_pack: EvidencePack

    def to_dict(self) -> dict:
        return self.evidence_pack.to_dict()


def _compute_policy_hash(policy: object) -> str:
    """Compute a stable hash of a policy dataclass for pack_id determinism."""
    import dataclasses

    parts = []
    for f in dataclasses.fields(policy):
        parts.append(f"{f.name}={getattr(policy, f.name)}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def compute_pack_id(
    retrieval_run_id: str,
    query_hash: str,
    item_identities: list[tuple[str, str]],
    selection_policy: EvidenceSelectionPolicy,
    context_policy: ContextAssemblyPolicy,
    budget: EvidenceBudget | None,
) -> str:
    """Compute a deterministic, order-sensitive pack_id from input and policy.

    pack_id = sha256(retrieval_run_id + query_hash + ordered item identities
                    + selection_policy_hash + context_policy_hash + budget_hash)

    item_identities must be in final pack order (retrieval_rank order).
    """
    parts = [
        retrieval_run_id,
        query_hash,
    ]
    # Hash in final pack order — order matters
    for doc_id, chunk_id in item_identities:
        parts.append(f"{doc_id}:{chunk_id}")
    parts.append(_compute_policy_hash(selection_policy))
    parts.append(_compute_policy_hash(context_policy))
    if budget is not None:
        parts.append(_compute_policy_hash(budget))
    else:
        parts.append("no_budget")

    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
