"""Evidence pack builder interface.

Defines the EvidencePackBuilder protocol that any evidence pack
implementation must satisfy.
"""

from typing import Protocol, runtime_checkable

from tracevault.evidence.models import (
    EvidencePackRequest,
    EvidencePackResponse,
)


@runtime_checkable
class EvidencePackBuilder(Protocol):
    """Protocol for evidence pack builders.

    Implementations must accept a RetrievalResponse (via EvidencePackRequest)
    and produce an EvidencePackResponse with full traceability.
    """

    def build(self, request: EvidencePackRequest) -> EvidencePackResponse:
        """Build an evidence pack from a retrieval response.

        Args:
            request: EvidencePackRequest containing the retrieval response
                and optional policies/budget.

        Returns:
            EvidencePackResponse with the assembled evidence pack.
        """
        ...
