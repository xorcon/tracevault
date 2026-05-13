"""In-memory evidence pack builder.

Transforms RetrievalResponse into EvidencePack with:
- Deterministic selection by retrieval rank
- Deduplication by (document_id, chunk_id) or raw_text_hash
- Budget enforcement via whole-item exclusion
- Mechanical context assembly without summarization
- Full traceability preservation
- No mutation of input RetrievalResponse
"""

import copy

from tracevault.evidence.audit import build_trace
from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceBudget,
    EvidenceExclusion,
    EvidenceExclusionReason,
    EvidenceGroup,
    EvidenceItem,
    EvidencePack,
    EvidencePackRequest,
    EvidencePackResponse,
    EvidenceSelectionPolicy,
    compute_pack_id,
)
from tracevault.evidence.policy import (
    default_context_policy,
    default_selection_policy,
)


def _result_to_evidence_item(result, response) -> EvidenceItem:
    """Convert a RetrievalResult into an EvidenceItem.

    Reads trace fields from result.trace (per-run audit data), not from
    candidate.metadata (stable evidence identity).
    """
    c = result.candidate
    t = result.trace
    return EvidenceItem(
        document_id=c.document_id,
        chunk_id=c.chunk_id,
        chunk_index=c.chunk_index,
        source_path=c.source_path,
        source_type=c.source_type,
        raw_text=c.raw_text,
        cleaned_text=c.cleaned_text,
        raw_text_hash=c.raw_text_hash,
        cleaned_text_hash=c.cleaned_text_hash,
        retrieval_run_id=result.retrieval_run_id,
        query_hash=result.query_hash,
        retrieval_source=t.retrieval_source,
        source_retrievers=list(t.source_retrievers),
        matched_fields=list(t.matched_fields),
        score=RetrievalScore(
            keyword_score=c.score.keyword_score,
            vector_score=c.score.vector_score,
            hybrid_score=c.score.hybrid_score,
            alpha=c.score.alpha,
            score_policy=c.score.score_policy,
        ),
        rank=result.rank,
        text_policy=response.text_policy,
        applied_filters=list(t.applied_filters),
        candidate_metadata=copy.deepcopy(c.metadata),
    )


def _dedup_key(item: EvidenceItem, policy: EvidenceSelectionPolicy) -> tuple:
    """Compute the deduplication key for an EvidenceItem."""
    if policy.deduplicate_by == "document_chunk":
        return (item.document_id, item.chunk_id)
    elif policy.deduplicate_by == "raw_text_hash":
        return (item.raw_text_hash,)
    else:
        return (item.document_id, item.chunk_id)


def _apply_budget(
    items: list[EvidenceItem],
    budget: EvidenceBudget,
    context_policy: ContextAssemblyPolicy,
) -> tuple[list[EvidenceItem], list[EvidenceExclusion]]:
    """Apply budget limits by excluding whole items.

    Returns (selected_items, exclusions).
    """
    selected: list[EvidenceItem] = []
    exclusions: list[EvidenceExclusion] = []

    raw_chars = 0
    cleaned_chars = 0
    context_chars = 0

    for item in items:
        item_raw = len(item.raw_text)
        item_cleaned = len(item.cleaned_text)
        item_context = 0
        if context_policy.include_raw_text:
            item_context += item_raw
        if context_policy.include_cleaned_text:
            item_context += item_cleaned

        # Check item count budget
        if budget.max_items is not None and len(selected) >= budget.max_items:
            exclusions.append(
                EvidenceExclusion(
                    document_id=item.document_id,
                    chunk_id=item.chunk_id,
                    reason=EvidenceExclusionReason.MAX_ITEMS_EXCEEDED,
                    budget_field="max_items",
                )
            )
            continue

        # Check raw chars budget
        if budget.max_raw_chars is not None and (raw_chars + item_raw) > budget.max_raw_chars:
            exclusions.append(
                EvidenceExclusion(
                    document_id=item.document_id,
                    chunk_id=item.chunk_id,
                    reason=EvidenceExclusionReason.MAX_RAW_CHARS_EXCEEDED,
                    budget_field="max_raw_chars",
                )
            )
            continue

        # Check cleaned chars budget
        if budget.max_cleaned_chars is not None and (cleaned_chars + item_cleaned) > budget.max_cleaned_chars:
            exclusions.append(
                EvidenceExclusion(
                    document_id=item.document_id,
                    chunk_id=item.chunk_id,
                    reason=EvidenceExclusionReason.MAX_CLEANED_CHARS_EXCEEDED,
                    budget_field="max_cleaned_chars",
                )
            )
            continue

        # Check context chars budget
        if budget.max_context_chars is not None and (context_chars + item_context) > budget.max_context_chars:
            exclusions.append(
                EvidenceExclusion(
                    document_id=item.document_id,
                    chunk_id=item.chunk_id,
                    reason=EvidenceExclusionReason.MAX_CONTEXT_CHARS_EXCEEDED,
                    budget_field="max_context_chars",
                )
            )
            continue

        selected.append(item)
        raw_chars += item_raw
        cleaned_chars += item_cleaned
        context_chars += item_context

    return selected, exclusions


def _assemble_context(
    items: list[EvidenceItem],
    context_policy: ContextAssemblyPolicy,
) -> str:
    """Assemble mechanical context string from evidence items.

    Format is inspectable and deterministic — no summarization or rewriting.
    """
    lines: list[str] = []

    for idx, item in enumerate(items, start=1):
        lines.append(f"[EVIDENCE {idx}]")
        lines.append(f"document_id: {item.document_id}")
        lines.append(f"chunk_id: {item.chunk_id}")
        lines.append(f"source_path: {item.source_path}")
        lines.append(f"retrieval_rank: {item.rank}")
        lines.append(f"retrieval_source: {item.retrieval_source}")
        lines.append(f"source_retrievers: {','.join(item.source_retrievers)}")
        lines.append(f"raw_text_hash: {item.raw_text_hash}")
        if item.cleaned_text_hash:
            lines.append(f"cleaned_text_hash: {item.cleaned_text_hash}")
        lines.append("")

        if context_policy.include_raw_text:
            lines.append("RAW_TEXT:")
            lines.append(item.raw_text)
            lines.append("")

        if context_policy.include_cleaned_text:
            lines.append("CLEANED_TEXT:")
            lines.append(item.cleaned_text)
            lines.append("")

    return "\n".join(lines)


# Import RetrievalScore here to avoid circular import
from tracevault.retrieval.models import RetrievalScore  # noqa: E402


class InMemoryEvidencePackBuilder:
    """In-memory evidence pack builder.

    Accepts RetrievalResponse, applies selection/dedup/budget policies,
    and produces an EvidencePack with full traceability.

    Guarantees:
    - Does not mutate RetrievalResponse, RetrievalResult, or CandidateEvidence
    - Deterministic output for same input and same policies
    - No wall-clock timestamps or random UUIDs
    - No answer/reasoning/citation-validation fields
    """

    def build(self, request: EvidencePackRequest) -> EvidencePackResponse:
        """Build an evidence pack from a retrieval response."""
        response = request.retrieval_response
        selection = request.selection_policy or default_selection_policy()
        context = request.context_policy or default_context_policy()
        budget = request.budget

        # Step 1: Convert RetrievalResult to EvidenceItem
        all_items: list[EvidenceItem] = []
        for result in response.results:
            item = _result_to_evidence_item(result, response)
            all_items.append(item)

        # Step 2: Order by retrieval_rank (default)
        if selection.order_by == "retrieval_rank":
            all_items.sort(key=lambda i: i.rank)

        # Step 3: Deduplicate — record exclusions for dropped duplicates
        seen: set[tuple] = set()
        deduped: list[EvidenceItem] = []
        duplicate_exclusions: list[EvidenceExclusion] = []
        for item in all_items:
            key = _dedup_key(item, selection)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
            else:
                # Record duplicate exclusion
                if selection.deduplicate_by == "document_chunk":
                    reason = EvidenceExclusionReason.DUPLICATE_DOCUMENT_CHUNK
                    detail = f"duplicate of (document_id={item.document_id}, chunk_id={item.chunk_id})"
                else:
                    reason = EvidenceExclusionReason.DUPLICATE_RAW_TEXT_HASH
                    detail = f"duplicate of raw_text_hash={item.raw_text_hash}"
                duplicate_exclusions.append(
                    EvidenceExclusion(
                        document_id=item.document_id,
                        chunk_id=item.chunk_id,
                        reason=reason,
                        detail=detail,
                    )
                )

        # Step 4: Apply budget
        selected, budget_exclusions = _apply_budget(deduped, budget or EvidenceBudget(), context)

        # Combine all exclusions: duplicates first, then budget
        all_exclusions = duplicate_exclusions + budget_exclusions

        # Step 5: Compute deterministic pack_id (order-sensitive)
        item_identities = [(i.document_id, i.chunk_id) for i in selected]
        pack_id = compute_pack_id(
            retrieval_run_id=response.retrieval_run_id,
            query_hash=response.query_hash,
            item_identities=item_identities,
            selection_policy=selection,
            context_policy=context,
            budget=budget,
        )

        # Step 6: Assemble context
        context_str = _assemble_context(selected, context)

        # Step 7: Build groups (single "all" group by default)
        groups = [EvidenceGroup(group_name="all", items=selected)] if selected else []

        # Step 8: Build trace — applied_filters preserved verbatim
        trace = build_trace(
            pack_id=pack_id,
            retrieval_run_id=response.retrieval_run_id,
            query=response.query,
            query_hash=response.query_hash,
            total_input_results=len(response.results),
            total_selected_items=len(selected),
            total_excluded_items=len(all_exclusions),
            exclusions=all_exclusions,
            selection_policy=selection,
            context_policy=context,
            budget=budget,
            text_policy=response.text_policy,
            applied_filters=response.applied_filters,
            pack_run_id=request.pack_run_id,
        )

        # Step 9: Assemble EvidencePack
        evidence_pack = EvidencePack(
            items=selected,
            groups=groups,
            context=context_str,
            trace=trace,
        )

        return EvidencePackResponse(evidence_pack=evidence_pack)
