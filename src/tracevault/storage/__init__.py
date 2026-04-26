"""Storage module.

Handles dual-context storage (raw_text and cleaned_text) with traceability.
Phase 2 will implement the storage backend.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backend.

    Supports dual-context storage:
    - raw_text: Original source evidence (immutable)
    - cleaned_text: Normalized semantic version for retrieval
    """

    def store_chunk(self, document_id: str, chunk_id: str, raw_text: str, cleaned_text: str, metadata: dict) -> None:
        """Store a knowledge chunk.

        Args:
            document_id: Source document identifier.
            chunk_id: Unique chunk identifier.
            raw_text: Original source text (source of truth).
            cleaned_text: Normalized text for retrieval.
            metadata: Additional metadata.
        """
        ...

    def get_chunk(self, document_id: str, chunk_id: str) -> tuple[str, str] | None:
        """Retrieve a chunk.

        Args:
            document_id: Source document identifier.
            chunk_id: Chunk identifier.

        Returns:
            Tuple of (raw_text, cleaned_text) or None if not found.
        """
        ...

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks for a document.

        Args:
            document_id: Document identifier.
        """
        ...
