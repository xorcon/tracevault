"""Data models for semantic refinement.

Defines structured types for chunks, refinement metadata, and results.

Key concepts:
- TextChunk: Represents a single chunk with raw_text (source of truth) and cleaned_text (retrieval aid)
- RefinementMetadata: Tracks how refinement was performed (method, version, warnings)
- RefinementResult: Container for refinement output with chunks and metadata
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

RefinementMethod = Literal["rule_based", "model_based", "none"]


@dataclass
class TextChunk:
    """A text chunk with dual-context storage.

    Attributes:
        chunk_id: Deterministic identifier (chunk_<document_id>_<chunk_index>)
        document_id: Parent document identifier
        chunk_index: Zero-based index within document
        raw_text: Original source text (source of truth, immutable)
        cleaned_text: Normalized text for retrieval (may be same as raw_text)
        start_offset: Character offset of chunk start in original document
        end_offset: Character offset of chunk end in original document
        raw_text_hash: SHA-256 hash of raw_text for integrity verification
        metadata: Additional chunk metadata
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    raw_text: str
    cleaned_text: str
    start_offset: int
    end_offset: int
    raw_text_hash: str
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def generate_chunk_id(document_id: str, chunk_index: int) -> str:
        """Generate deterministic chunk ID.

        Format: chunk_<document_id>_<chunk_index>

        Example: chunk_doc_abc123_0
        """
        return f"chunk_{document_id}_{chunk_index}"

    @staticmethod
    def compute_raw_hash(raw_text: str) -> str:
        """Compute SHA-256 hash of raw text."""
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify raw_text hash matches stored hash."""
        return self.raw_text_hash == self.compute_raw_hash(self.raw_text)


@dataclass
class RefinementMetadata:
    """Metadata tracking how refinement was performed.

    Attributes:
        refinement_method: Method used (rule_based, model_based, none)
        prompt_version: Version of refinement prompt/rules applied
        model_name: Model name if model-based refinement used (None for rule-based)
        created_at: ISO 8601 UTC timestamp
        warnings: List of warnings during refinement (e.g., "added_words_detected")
        no_new_facts_checked: Whether no-new-facts safeguard was applied
        source_raw_hash: Hash of original raw text for traceability
        cleaned_text_length: Length of cleaned text
        raw_text_length: Length of raw text
    """

    refinement_method: RefinementMethod
    prompt_version: str
    model_name: str | None
    created_at: str
    warnings: list[str] = field(default_factory=list)
    no_new_facts_checked: bool = False
    source_raw_hash: str | None = None
    cleaned_text_length: int = 0
    raw_text_length: int = 0

    @staticmethod
    def get_current_timestamp() -> str:
        """Get current UTC time as ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()


@dataclass
class RefinementResult:
    """Result of refining a document.

    Attributes:
        document_id: Source document identifier
        chunks: List of refined text chunks
        metadata: Overall refinement metadata
        total_chunks: Number of chunks produced
        total_raw_chars: Total characters in raw text
        total_cleaned_chars: Total characters in cleaned text
    """

    document_id: str
    chunks: list[TextChunk]
    metadata: RefinementMetadata
    total_chunks: int
    total_raw_chars: int
    total_cleaned_chars: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "chunk_index": c.chunk_index,
                    "raw_text": c.raw_text,
                    "cleaned_text": c.cleaned_text,
                    "start_offset": c.start_offset,
                    "end_offset": c.end_offset,
                    "raw_text_hash": c.raw_text_hash,
                    "metadata": c.metadata,
                }
                for c in self.chunks
            ],
            "metadata": {
                "refinement_method": self.metadata.refinement_method,
                "prompt_version": self.metadata.prompt_version,
                "model_name": self.metadata.model_name,
                "created_at": self.metadata.created_at,
                "warnings": self.metadata.warnings,
                "no_new_facts_checked": self.metadata.no_new_facts_checked,
                "source_raw_hash": self.metadata.source_raw_hash,
                "raw_text_length": self.metadata.raw_text_length,
                "cleaned_text_length": self.metadata.cleaned_text_length,
            },
            "total_chunks": self.total_chunks,
            "total_raw_chars": self.total_raw_chars,
            "total_cleaned_chars": self.total_cleaned_chars,
        }
