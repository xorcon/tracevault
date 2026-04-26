"""Data models for ingestion.

Defines structured types for documents, ingestion results, and manifests.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Literal

DocumentStatus = Literal["new", "unchanged", "changed", "skipped", "error"]


@dataclass
class DocumentRecord:
    """Record of an ingested document.

    Attributes:
        document_id: Stable identifier derived from source path hash and content hash.
        source_path: Normalized relative path to source file.
        content_hash: SHA-256 hash of raw content.
        size_bytes: File size in bytes.
        modified_time: Filesystem modification timestamp (ISO 8601).
        ingested_at: Ingestion timestamp (ISO 8601 UTC).
        source_type: File extension type (txt, md, markdown).
    """

    document_id: str
    source_path: str
    content_hash: str
    size_bytes: int
    modified_time: str
    ingested_at: str
    source_type: str

    @staticmethod
    def generate_document_id(source_path: str, content_hash: str) -> str:
        """Generate collision-resistant document ID from canonical path and content.

        Format: doc_<path_hash_12>_<content_hash_12>

        - path_hash: SHA-256 of canonical source path (first 12 hex chars)
        - content_hash: SHA-256 of raw content (first 12 hex chars)

        Guarantees:
        - Same path + same content = same document_id
        - Same path + different content = different document_id
        - Different paths + same content = different document_id
        - No collisions between files with same basename in different directories
        """
        # Hash the canonical source path to avoid collisions from same-named files
        path_hash = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:12]
        content_prefix = content_hash[:12]
        return f"doc_{path_hash}_{content_prefix}"


@dataclass
class IngestResult:
    """Result of processing a single file.

    Attributes:
        source_path: Path that was attempted.
        status: Processing status.
        document_record: Document details if successful.
        error: Error message if failed.
    """

    source_path: str
    status: DocumentStatus
    document_record: DocumentRecord | None = None
    error: str | None = None


@dataclass
class IngestSummary:
    """Summary of a directory/file ingestion run.

    Attributes:
        total_files: Total files encountered.
        new_count: Files ingested as new.
        unchanged_count: Files unchanged since last ingest.
        changed_count: Files with modified content.
        skipped_count: Unsupported or ignored files.
        error_count: Files that failed to process.
        results: Detailed results for each file.
    """

    total_files: int
    new_count: int
    unchanged_count: int
    changed_count: int
    skipped_count: int
    error_count: int
    results: list[IngestResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_files": self.total_files,
            "new_count": self.new_count,
            "unchanged_count": self.unchanged_count,
            "changed_count": self.changed_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "results": [
                {
                    "source_path": r.source_path,
                    "status": r.status,
                    "document_id": r.document_record.document_id if r.document_record else None,
                    "content_hash": r.document_record.content_hash if r.document_record else None,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


@dataclass
class ManifestEntry:
    """Entry in the ingest manifest.

    Attributes:
        source_path: Normalized source path.
        content_hash: SHA-256 hash.
        size_bytes: File size.
        modified_time: Last modification time.
        last_ingested: Last successful ingestion time.
    """

    source_path: str
    content_hash: str
    size_bytes: int
    modified_time: str
    last_ingested: str
