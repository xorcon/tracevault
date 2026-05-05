"""Audit trace helpers for evidence packs."""

from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceBudget,
    EvidenceExclusion,
    EvidencePackTrace,
    EvidenceSelectionPolicy,
    TextRetrievalPolicy,
)


def build_trace(
    pack_id: str,
    retrieval_run_id: str,
    query: str,
    query_hash: str,
    total_input_results: int,
    total_selected_items: int,
    total_excluded_items: int,
    exclusions: list[EvidenceExclusion],
    selection_policy: EvidenceSelectionPolicy,
    context_policy: ContextAssemblyPolicy,
    budget: EvidenceBudget | None,
    text_policy: TextRetrievalPolicy,
    applied_filters: list[str],
    pack_run_id: str = "",
) -> EvidencePackTrace:
    """Build an EvidencePackTrace from builder parameters."""
    return EvidencePackTrace(
        pack_id=pack_id,
        retrieval_run_id=retrieval_run_id,
        query=query,
        query_hash=query_hash,
        total_input_results=total_input_results,
        total_selected_items=total_selected_items,
        total_excluded_items=total_excluded_items,
        exclusions=list(exclusions),
        selection_policy=selection_policy,
        context_policy=context_policy,
        budget=budget,
        text_policy=text_policy,
        applied_filters=list(applied_filters),
        pack_run_id=pack_run_id,
    )
