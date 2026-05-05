"""Evidence pack module.

Phase 5 — Evidence Pack & Grounded Context Assembly.

Transforms RetrievalResponse into structured EvidencePack objects
with full traceability, deterministic selection, budget control,
and mechanical context assembly.

Does NOT implement:
- answer generation
- reasoning
- LLM calls
- citation validation
- claim validation
- unsupported claim detection
- hallucination scoring
- vector DB integration
"""

from tracevault.evidence.builder import InMemoryEvidencePackBuilder
from tracevault.evidence.interfaces import EvidencePackBuilder
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
    EvidencePackTrace,
    EvidenceSelectionPolicy,
)
from tracevault.evidence.policy import (
    default_context_policy,
    default_selection_policy,
)

__all__ = [
    # Models
    "EvidencePackRequest",
    "EvidencePackResponse",
    "EvidencePack",
    "EvidenceItem",
    "EvidenceGroup",
    "EvidencePackTrace",
    "EvidenceSelectionPolicy",
    "ContextAssemblyPolicy",
    "EvidenceBudget",
    "EvidenceExclusion",
    "EvidenceExclusionReason",
    # Interfaces
    "EvidencePackBuilder",
    # Implementations
    "InMemoryEvidencePackBuilder",
    # Policy defaults
    "default_selection_policy",
    "default_context_policy",
]
