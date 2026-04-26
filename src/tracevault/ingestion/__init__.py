"""Ingestion module.

Handles document loading, metadata extraction, and manifest creation.
Phase 2 will implement differential ingest and hashing.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentLoader(Protocol):
    """Protocol for document loading."""

    def load(self, source_path: str) -> str:
        """Load document content.

        Args:
            source_path: Path to the document.

        Returns:
            Raw document content.
        """
        ...

    def get_metadata(self, source_path: str) -> dict:
        """Extract metadata from document.

        Args:
            source_path: Path to the document.

        Returns:
            Metadata dictionary.
        """
        ...
