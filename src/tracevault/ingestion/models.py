"""Data models for ingestion.

Defines structured types for documents, ingestion results, and manifests.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DocumentStatus = Literal["new", "unchanged", "changed", "skipped", "error"]


@dataclass
class DocumentRecord:
    """Record of an ingested document.

    Attributes:
        document_id: Stable identifier (path-based with hash suffix).
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
        """Generate stable document ID from path and hash.

        Format: path-without-extension-hash[:8]
        """
        path = Path(source_path)
        name = path.stem.replace("/", "_").replace("\\", "_")
        return f"{name[:50]}_{content_hash[:16]}"


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
