"""Default policy instances for evidence pack construction."""

from tracevault.evidence.models import (
    ContextAssemblyPolicy,
    EvidenceSelectionPolicy,
)


def default_selection_policy() -> EvidenceSelectionPolicy:
    """Return the default EvidenceSelectionPolicy.

    order_by = retrieval_rank
    deduplicate_by = document_chunk
    """
    return EvidenceSelectionPolicy(
        order_by="retrieval_rank",
        deduplicate_by="document_chunk",
    )


def default_context_policy() -> ContextAssemblyPolicy:
    """Return the default ContextAssemblyPolicy.

    include_raw_text = True
    include_cleaned_text = True
    """
    return ContextAssemblyPolicy(
        include_raw_text=True,
        include_cleaned_text=True,
    )
