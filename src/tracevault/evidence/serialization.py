"""JSON serialization for evidence packs.

Provides round-trip serialization that preserves all audit metadata.
"""

import json

from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceBudget,
    EvidenceExclusion,
    EvidenceGroup,
    EvidenceItem,
    EvidencePack,
    EvidencePackResponse,
    EvidencePackTrace,
    EvidenceSelectionPolicy,
)
from tracevault.retrieval.models import RetrievalScore, TextRetrievalPolicy


def serialize_evidence_pack(evidence_pack: EvidencePack) -> str:
    """Serialize an EvidencePack to a JSON string.

    Preserves all audit metadata for round-trip safety.
    """
    return json.dumps(evidence_pack.to_dict(), indent=2, ensure_ascii=False)


def serialize_evidence_pack_response(response: EvidencePackResponse) -> str:
    """Serialize an EvidencePackResponse to a JSON string."""
    return json.dumps(response.to_dict(), indent=2, ensure_ascii=False)


def deserialize_evidence_pack(data: dict) -> EvidencePack:
    """Deserialize a dictionary into an EvidencePack.

    Reconstructs all model objects from the serialized form.
    """
    items = [deserialize_evidence_item(i) for i in data.get("items", [])]
    groups = [deserialize_evidence_group(g) for g in data.get("groups", [])]
    trace = deserialize_evidence_pack_trace(data.get("trace", {}))

    return EvidencePack(
        items=items,
        groups=groups,
        context=data.get("context", ""),
        trace=trace,
    )


def deserialize_evidence_item(d: dict) -> EvidenceItem:
    """Deserialize a dictionary into an EvidenceItem."""
    score_d = d.get("score", {})
    return EvidenceItem(
        document_id=d.get("document_id", ""),
        chunk_id=d.get("chunk_id", ""),
        chunk_index=d.get("chunk_index", 0),
        source_path=d.get("source_path", ""),
        source_type=d.get("source_type", ""),
        raw_text=d.get("raw_text", ""),
        cleaned_text=d.get("cleaned_text", ""),
        raw_text_hash=d.get("raw_text_hash", ""),
        cleaned_text_hash=d.get("cleaned_text_hash"),
        retrieval_run_id=d.get("retrieval_run_id", ""),
        query_hash=d.get("query_hash", ""),
        retrieval_source=d.get("retrieval_source", ""),
        source_retrievers=d.get("source_retrievers", []),
        matched_fields=d.get("matched_fields", []),
        score=RetrievalScore(
            keyword_score=score_d.get("keyword_score", 0.0),
            vector_score=score_d.get("vector_score", 0.0),
            hybrid_score=score_d.get("hybrid_score", 0.0),
            alpha=score_d.get("alpha", 0.5),
            score_policy=score_d.get("score_policy", ""),
        ),
        rank=d.get("rank", 0),
        text_policy=TextRetrievalPolicy(mode=d.get("text_policy", "DUAL_CONTEXT")),
        applied_filters=d.get("applied_filters", []),
        candidate_metadata=d.get("candidate_metadata", {}),
    )


def deserialize_evidence_group(d: dict) -> EvidenceGroup:
    """Deserialize a dictionary into an EvidenceGroup."""
    items = [deserialize_evidence_item(i) for i in d.get("items", [])]
    return EvidenceGroup(
        group_name=d.get("group_name", ""),
        items=items,
    )


def deserialize_evidence_pack_trace(d: dict) -> EvidencePackTrace:
    """Deserialize a dictionary into an EvidencePackTrace."""
    sel_d = d.get("selection_policy", {})
    ctx_d = d.get("context_policy", {})
    budget_d = d.get("budget")

    budget = None
    if budget_d:
        budget = EvidenceBudget(
            max_items=budget_d.get("max_items"),
            max_raw_chars=budget_d.get("max_raw_chars"),
            max_cleaned_chars=budget_d.get("max_cleaned_chars"),
            max_context_chars=budget_d.get("max_context_chars"),
        )

    exclusions = [
        EvidenceExclusion(
            document_id=e.get("document_id", ""),
            chunk_id=e.get("chunk_id", ""),
            reason=e.get("reason", ""),
            budget_field=e.get("budget_field", ""),
            detail=e.get("detail", ""),
        )
        for e in d.get("exclusions", [])
    ]

    return EvidencePackTrace(
        pack_id=d.get("pack_id", ""),
        retrieval_run_id=d.get("retrieval_run_id", ""),
        query=d.get("query", ""),
        query_hash=d.get("query_hash", ""),
        total_input_results=d.get("total_input_results", 0),
        total_selected_items=d.get("total_selected_items", 0),
        total_excluded_items=d.get("total_excluded_items", 0),
        exclusions=exclusions,
        selection_policy=EvidenceSelectionPolicy(
            order_by=sel_d.get("order_by", "retrieval_rank"),
            deduplicate_by=sel_d.get("deduplicate_by", "document_chunk"),
        ),
        context_policy=ContextAssemblyPolicy(
            include_raw_text=ctx_d.get("include_raw_text", True),
            include_cleaned_text=ctx_d.get("include_cleaned_text", True),
        ),
        budget=budget,
        text_policy=TextRetrievalPolicy(mode=d.get("text_policy", "DUAL_CONTEXT")),
        applied_filters=d.get("applied_filters", ""),
        pack_run_id=d.get("pack_run_id", ""),
    )
